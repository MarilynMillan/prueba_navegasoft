# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, timedelta, time
from operator import itemgetter

import pytz

from odoo import fields, models
from odoo.osv.expression import AND, OR
from odoo.tools import float_is_zero


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _get_employee_tz(self, employee):
        tz_name = (
            getattr(employee, "tz", False)
            or getattr(getattr(employee, "resource_calendar_id", False), "tz", False)
            or getattr(getattr(getattr(employee, "company_id", False), "resource_calendar_id", False), "tz", False)
            or "UTC"
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _is_public_holiday_day(self, employee, attendance_date):
        tz = self._get_employee_tz(employee)
        local_start = tz.localize(datetime.combine(attendance_date, time.min))
        local_end = tz.localize(datetime.combine(attendance_date + timedelta(days=1), time.min))
        start_utc = local_start.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = local_end.astimezone(pytz.UTC).replace(tzinfo=None)

        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if calendar:
            leave = self.env["resource.calendar.leaves"].search([
                ("calendar_id", "=", calendar.id),
                ("resource_id", "=", False),
                ("date_from", "<", end_utc),
                ("date_to", ">", start_utc),
            ], limit=1)
            if leave:
                return True

        if "hr.holidays.public.line" in self.env:
            hol = self.env["hr.holidays.public.line"].search([
                ("date", "=", attendance_date),
            ], limit=1)
            if hol:
                return True

        return False

    def _update_overtime(self, employee_attendance_dates=None):
        if employee_attendance_dates is None:
            employee_attendance_dates = self._get_attendances_dates()

        overtime_to_unlink = self.env["hr.attendance.overtime"]
        overtime_vals_list = []
        affected_employees = self.env["hr.employee"]

        for emp, attendance_dates in employee_attendance_dates.items():
            attendance_domain = []
            for attendance_date in attendance_dates:
                attendance_domain = OR([attendance_domain, [
                    ("check_in", ">=", attendance_date[0]), ("check_in", "<", attendance_date[0] + timedelta(hours=24)),
                ]])
            attendance_domain = AND([[("employee_id", "=", emp.id)], attendance_domain])

            attendances_per_day = defaultdict(lambda: self.env["hr.attendance"])
            all_attendances = self.env["hr.attendance"].search(attendance_domain)
            for attendance in all_attendances:
                check_in_day_start = attendance._get_day_start_and_day(attendance.employee_id, attendance.check_in)
                attendances_per_day[check_in_day_start[1]] += attendance

            start = pytz.utc.localize(min(attendance_dates, key=itemgetter(0))[0])
            stop = pytz.utc.localize(max(attendance_dates, key=itemgetter(0))[0] + timedelta(hours=24))

            expected_attendances = emp._employee_attendance_intervals(start, stop)

            working_times = defaultdict(list)
            for expected_attendance in expected_attendances:
                working_times[expected_attendance[0].date()].append(expected_attendance[:2])

            overtimes = self.env["hr.attendance.overtime"].sudo().search([
                ("employee_id", "=", emp.id),
                ("date", "in", [day_data[1] for day_data in attendance_dates]),
                ("adjustment", "=", False),
            ])

            company_threshold = emp.company_id.overtime_company_threshold / 60.0
            employee_threshold = emp.company_id.overtime_employee_threshold / 60.0

            for day_data in attendance_dates:
                attendance_date = day_data[1]
                attendances = attendances_per_day.get(attendance_date, self.browse())
                unfinished_shifts = attendances.filtered(lambda a: not a.check_out)
                overtime_duration = 0
                overtime_duration_real = 0

                if self._is_public_holiday_day(emp, attendance_date):
                    working_times[attendance_date] = []

                if not unfinished_shifts and attendances:
                    if emp.is_fully_flexible:
                        work_duration = 0
                        for attendance in attendances:
                            local_check_in = pytz.utc.localize(attendance.check_in)
                            local_check_out = pytz.utc.localize(attendance.check_out)
                            work_duration += (local_check_out - local_check_in).total_seconds() / 3600.0
                        if not self._is_public_holiday_day(emp, attendance_date):
                            overtime_duration = work_duration - emp.resource_id.calendar_id.hours_per_day
                            overtime_duration_real = overtime_duration
                        else:
                            overtime_duration = work_duration
                            overtime_duration_real = work_duration
                    elif not working_times[attendance_date]:
                        overtime_duration = sum(attendances.mapped("worked_hours"))
                        overtime_duration_real = overtime_duration
                    else:
                        pre_work_time, work_duration, post_work_time, planned_work_duration = attendances._get_pre_post_work_time(
                            emp, working_times, attendance_date
                        )
                        overtime_duration = work_duration - planned_work_duration
                        if pre_work_time > company_threshold:
                            overtime_duration += pre_work_time
                        if post_work_time > employee_threshold:
                            overtime_duration += post_work_time
                        overtime_duration_real = sum(attendances.mapped("worked_hours")) - planned_work_duration

                overtime = overtimes.filtered(lambda o: o.date == attendance_date)
                if not float_is_zero(overtime_duration, 2) or unfinished_shifts:
                    if unfinished_shifts:
                        overtime_duration = 0
                    if not overtime and overtime_duration:
                        overtime_vals_list.append({
                            "employee_id": emp.id,
                            "date": attendance_date,
                            "duration": overtime_duration,
                            "duration_real": overtime_duration_real,
                        })
                    elif overtime:
                        overtime.sudo().write({
                            "duration": overtime_duration,
                            "duration_real": overtime_duration,
                        })
                        affected_employees |= overtime.employee_id
                elif overtime:
                    overtime_to_unlink |= overtime

        created_overtimes = self.env["hr.attendance.overtime"].sudo().create(overtime_vals_list)
        affected_employees |= self.env["hr.employee"].browse(
            created_overtimes.employee_id.ids + overtime_to_unlink.employee_id.ids
        )
        overtime_to_unlink.sudo().unlink()

        self.env.add_to_compute(self._fields["overtime_hours"], affected_employees.attendance_ids)
        self.env.add_to_compute(self._fields["validated_overtime_hours"], affected_employees.attendance_ids)
