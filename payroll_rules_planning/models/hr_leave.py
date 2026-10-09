# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time, timedelta
import pytz

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _payroll_rules_leave_tz(self):
        self.ensure_one()
        tz_name = (
            getattr(self.employee_id, "tz", False)
            or getattr(getattr(self.employee_id, "resource_calendar_id", False), "tz", False)
            or getattr(getattr(self.company_id, "resource_calendar_id", False), "tz", False)
            or "UTC"
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _payroll_rules_is_exact_hour_request(self):
        self.ensure_one()
        return bool(
            self.employee_id
            and self.holiday_status_id
            and self.holiday_status_id.time_type == "other"
            and self.request_unit_hours
            and self.request_date_from
            and self.request_date_to
            and self.request_hour_from not in (False, None)
            and self.request_hour_to not in (False, None)
        )

    def _payroll_rules_hour_request_range(self):
        self.ensure_one()
        if not self._payroll_rules_is_exact_hour_request():
            return False, False

        tz = self._payroll_rules_leave_tz()
        start_hour = float(self.request_hour_from)
        stop_hour = float(self.request_hour_to)

        start_dt = datetime.combine(self.request_date_from, time.min) + timedelta(hours=start_hour)
        stop_dt = datetime.combine(self.request_date_to, time.min) + timedelta(hours=stop_hour)
        if stop_dt <= start_dt:
            stop_dt += timedelta(days=1)

        start_utc = tz.localize(start_dt).astimezone(pytz.UTC).replace(tzinfo=None)
        stop_utc = tz.localize(stop_dt).astimezone(pytz.UTC).replace(tzinfo=None)
        return start_utc, stop_utc

    def _payroll_rules_planning_slots_for_leave(self, leave):
        Slot = self.env["planning.slot"].sudo()
        range_start, range_stop = leave._payroll_rules_effective_leave_range()
        if not leave.employee_id or not range_start or not range_stop:
            return Slot.browse()

        domain = [
            ("employee_id", "=", leave.employee_id.id),
            ("start_datetime", "<", range_stop),
            ("end_datetime", ">", range_start),
        ]
        if "approval_state" in Slot._fields:
            domain.append(("approval_state", "not in", ["rejected", "cancelled"]))
        if "company_id" in Slot._fields and leave.company_id:
            domain.append(("company_id", "in", [False, leave.company_id.id]))
        return Slot.search(domain)

    def _payroll_rules_effective_leave_range(self):
        self.ensure_one()
        leave_type = self.holiday_status_id
        if (
            leave_type
            and self.request_date_from
            and self.request_date_to
            and leave_type.time_type == "leave"
            and not self.request_unit_hours
            and not getattr(self, "request_unit_half", False)
        ):
            tz_name = (
                getattr(self.employee_id, "tz", False)
                or getattr(getattr(self.employee_id, "resource_calendar_id", False), "tz", False)
                or getattr(getattr(self.company_id, "resource_calendar_id", False), "tz", False)
                or "UTC"
            )
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            start_local = datetime.combine(self.request_date_from, time(0, 0, 0))
            stop_local = datetime.combine(self.request_date_to, time(23, 59, 59))
            return (
                tz.localize(start_local).astimezone(pytz.UTC).replace(tzinfo=None),
                tz.localize(stop_local).astimezone(pytz.UTC).replace(tzinfo=None),
            )
        return self.date_from, self.date_to

    def _payroll_rules_requested_leave_duration_hours(self):
        self.ensure_one()
        if self._payroll_rules_is_exact_hour_request():
            start_utc, stop_utc = self._payroll_rules_hour_request_range()
            if start_utc and stop_utc:
                return max(0.0, (stop_utc - start_utc).total_seconds() / 3600.0)
        if (
            self.holiday_status_id
            and self.holiday_status_id.time_type == "leave"
            and self.request_date_from
            and self.request_date_to
            and not self.request_unit_hours
            and not getattr(self, "request_unit_half", False)
        ):
            total_days = (self.request_date_to - self.request_date_from).days + 1
            return float(total_days * 24)
        if self.date_from and self.date_to:
            return max(0.0, (self.date_to - self.date_from).total_seconds() / 3600.0)
        return 0.0

    def _payroll_rules_cleanup_planning_work_entries_during_leave(self):
        for leave in self.filtered(lambda l: l.employee_id and l.date_from and l.date_to and l.state == "validate"):
            slots = leave._payroll_rules_planning_slots_for_leave(leave).filtered(
                lambda s: getattr(s, "approval_state", False) == "approved"
            )
            for slot in slots:
                slot._cleanup_work_entries_for_slot(
                    only_types=None,
                    only_draft=False,
                    force_admin=True,
                )
                slot.sudo().write({
                    "work_entries_generated": False,
                    "recargos_generated": False,
                })

    def _payroll_rules_ensure_validated_leave_work_entries(self):
        WorkEntry = self.env["hr.work.entry"].sudo()
        for leave in self.filtered(
            lambda l: l.state == "validate"
            and l.employee_id
            and l.holiday_status_id
            and l.holiday_status_id.time_type == "leave"
            and l.request_date_from
            and l.request_date_to
            and not l.request_unit_hours
            and not getattr(l, "request_unit_half", False)
        ):
            active_entries = WorkEntry.search([
                ("leave_id", "=", leave.id),
                ("active", "=", True),
            ], order="date_start, id")

            range_start, range_stop = leave._payroll_rules_effective_leave_range()
            if not range_start or not range_stop or range_stop <= range_start:
                continue

            contracts = leave.employee_id.sudo()._get_contracts(range_start, range_stop, states=["open", "close"])
            contract = contracts[:1] if contracts else self.env["hr.contract"]
            work_entry_type = leave.holiday_status_id.work_entry_type_id
            if not work_entry_type:
                continue

            desired_vals = {
                "name": "%s: %s" % (work_entry_type.name, leave.employee_id.name),
                "employee_id": leave.employee_id.id,
                "work_entry_type_id": work_entry_type.id,
                "date_start": range_start,
                "date_stop": range_stop,
                "leave_id": leave.id,
                "company_id": leave.company_id.id,
                "contract_id": contract.id if contract else False,
                "state": "draft",
                "duration": leave._payroll_rules_requested_leave_duration_hours(),
            }

            if active_entries:
                survivor = active_entries[0]
                vals_to_write = {}
                for field_name, value in desired_vals.items():
                    current_value = survivor[field_name]
                    if hasattr(current_value, "id"):
                        current_value = current_value.id
                    if current_value != value:
                        vals_to_write[field_name] = value
                if vals_to_write:
                    survivor.with_context(
                        skip_full_day_leave_normalization=True,
                        skip_worked_time_leave_normalization=True,
                    ).sudo().write(vals_to_write)

                duplicates = active_entries - survivor
                if duplicates:
                    duplicates.sudo()._soft_remove_entries()
                continue

            WorkEntry.create([desired_vals])

    def _payroll_rules_ensure_validated_worked_time_work_entries(self):
        WorkEntry = self.env["hr.work.entry"].sudo()
        for leave in self.filtered(
            lambda l: l.state == "validate"
            and l.employee_id
            and l.holiday_status_id
            and l.holiday_status_id.time_type == "other"
            and l.date_from
            and l.date_to
        ):
            active_entries = WorkEntry.search([
                ("leave_id", "=", leave.id),
                ("active", "=", True),
            ], order="date_start, id")

            range_start, range_stop = leave._payroll_rules_hour_request_range()
            if not range_start or not range_stop:
                range_start, range_stop = leave.date_from, leave.date_to
            if not range_start or not range_stop or range_stop <= range_start:
                continue

            contracts = leave.employee_id.sudo()._get_contracts(range_start, range_stop, states=["open", "close"])
            contract = contracts[:1] if contracts else self.env["hr.contract"]
            work_entry_type = leave.holiday_status_id.work_entry_type_id
            if not work_entry_type:
                continue

            desired_vals = {
                "name": "%s: %s" % (work_entry_type.name, leave.employee_id.name),
                "employee_id": leave.employee_id.id,
                "work_entry_type_id": work_entry_type.id,
                "date_start": range_start,
                "date_stop": range_stop,
                "leave_id": leave.id,
                "company_id": leave.company_id.id,
                "contract_id": contract.id if contract else False,
                "state": "draft",
                "duration": leave._payroll_rules_requested_leave_duration_hours(),
            }

            if active_entries:
                survivor = active_entries[0]
                vals_to_write = {}
                for field_name, value in desired_vals.items():
                    current_value = survivor[field_name]
                    if hasattr(current_value, "id"):
                        current_value = current_value.id
                    if current_value != value:
                        vals_to_write[field_name] = value
                if vals_to_write:
                    survivor.with_context(
                        skip_full_day_leave_normalization=True,
                        skip_worked_time_leave_normalization=True,
                    ).sudo().write(vals_to_write)

                duplicates = active_entries - survivor
                if duplicates:
                    duplicates.sudo()._soft_remove_entries()
                survivor._normalize_worked_time_leave_entries()
                continue

            created = WorkEntry.create([desired_vals])
            created._normalize_worked_time_leave_entries()

    def _payroll_rules_recheck_work_entry_conflicts(self):
        WorkEntry = self.env["hr.work.entry"].sudo()
        for leave in self.filtered(lambda l: l.employee_id and l.date_from and l.date_to):
            impacted = WorkEntry.search([
                ("employee_id", "=", leave.employee_id.id),
                ("date_start", "<", leave.date_to + timedelta(days=1)),
                ("date_stop", ">", leave.date_from - timedelta(days=1)),
                ("active", "=", True),
                ("state", "not in", ["validated", "cancelled"]),
            ])
            if not impacted:
                continue
            impacted.filtered(lambda w: w.state == "conflict")._reset_conflicting_state()
            impacted._check_if_error()
            impacted._clear_false_conflicts()

    def _payroll_rules_restore_planning_work_entries_after_leave_release(self):
        validated_states = ["validate"]
        for leave in self.filtered(lambda l: l.employee_id and l.date_from and l.date_to):
            slots = leave._payroll_rules_planning_slots_for_leave(leave).filtered(
                lambda s: getattr(s, "approval_state", False) == "approved" and not getattr(s, "is_rest_day", False)
            )
            for slot in slots:
                overlapping_validated = self.env["hr.leave"].sudo().search_count([
                    ("id", "!=", leave.id),
                    ("employee_id", "=", leave.employee_id.id),
                    ("state", "in", validated_states),
                    ("date_from", "<", slot.end_datetime),
                    ("date_to", ">", slot.start_datetime),
                ])
                if overlapping_validated:
                    continue

                slot.sudo().write({
                    "work_entries_generated": False,
                    "recargos_generated": False,
                })
                slot._ensure_work_entries_once()
                slot._generate_recargo_work_entries_once()

    # Alias de compatibilidad interna.
    def _cleanup_planning_work_entries_during_leave(self):
        return self._payroll_rules_cleanup_planning_work_entries_during_leave()

    def _ensure_validated_leave_work_entries(self):
        return self._payroll_rules_ensure_validated_leave_work_entries()

    def _ensure_validated_worked_time_work_entries(self):
        return self._payroll_rules_ensure_validated_worked_time_work_entries()

    def _recheck_work_entry_conflicts(self):
        return self._payroll_rules_recheck_work_entry_conflicts()

    def _restore_planning_work_entries_after_leave_release(self):
        return self._payroll_rules_restore_planning_work_entries_after_leave_release()

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(check_leave_type=check_leave_type, resource_calendar=resource_calendar)

        for leave in self:
            leave_type = leave.holiday_status_id
            if not leave_type or leave_type.time_type != "other":
                continue
            if not leave.request_unit_hours:
                continue
            if leave.request_hour_from in (False, None) or leave.request_hour_to in (False, None):
                continue

            requested_hours = leave._payroll_rules_requested_leave_duration_hours()
            calendar = resource_calendar or leave.resource_calendar_id or leave.employee_id.resource_calendar_id or leave.company_id.resource_calendar_id
            hours_per_day = getattr(calendar, "hours_per_day", 8.0) or 8.0
            requested_days = (requested_hours / hours_per_day) if hours_per_day else 0.0

            if requested_hours:
                result[leave.id] = (requested_days, requested_hours)

        return result

    def action_validate(self, check_state=True):
        res = super().action_validate(check_state=check_state)
        self._payroll_rules_ensure_validated_leave_work_entries()
        self._payroll_rules_ensure_validated_worked_time_work_entries()
        self._payroll_rules_cleanup_planning_work_entries_during_leave()
        self._payroll_rules_recheck_work_entry_conflicts()
        return res

    def action_refuse(self):
        leaves_to_restore = self.filtered(lambda l: l.state == "validate")
        res = super().action_refuse()
        leaves_to_restore._payroll_rules_restore_planning_work_entries_after_leave_release()
        leaves_to_restore._payroll_rules_recheck_work_entry_conflicts()
        return res

    def action_reset_confirm(self):
        leaves_to_restore = self.filtered(lambda l: l.state == "validate")
        res = super().action_reset_confirm()
        leaves_to_restore._payroll_rules_restore_planning_work_entries_after_leave_release()
        leaves_to_restore._payroll_rules_recheck_work_entry_conflicts()
        return res

    def _action_user_cancel(self, reason):
        leaves_to_restore = self.filtered(lambda l: l.state == "validate")
        res = super()._action_user_cancel(reason)
        leaves_to_restore._payroll_rules_restore_planning_work_entries_after_leave_release()
        leaves_to_restore._payroll_rules_recheck_work_entry_conflicts()
        return res
