# -*- coding: utf-8 -*-
import calendar

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from datetime import date, time, datetime, timedelta
import pytz
import itertools
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


# ============================================================
# hr.work.entry.type — campos adicionales
# ============================================================
class HrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    allow_overlap = fields.Boolean(
        string="Permitir solapamiento",
        help="Permite que este tipo coincida con otras entradas sin generar conflicto.",
    )
    count_by_days = fields.Boolean(
        string="Contar por días",
        help="Permite contar días únicos en lugar de horas.",
    )

    @api.model
    def sync_payroll_rules_planning_types(self):
        definitions = [
            {
                "xmlid": "payroll_rules_planning.work_entry_type_hrn",
                "name": "Recargo Nocturno",
                "code": "HRN",
            },
            {
                "xmlid": "payroll_rules_planning.work_entry_type_hrndf",
                "name": "Recargo Nocturno Dominical / Festivo",
                "code": "HRNDF",
            },
            {
                "xmlid": "payroll_rules_planning.work_entry_type_hrddf",
                "name": "Recargo Diurno Dominical / Festivo",
                "code": "HRDDF",
            },
        ]
        ir_model_data = self.env["ir.model.data"].sudo()

        for definition in definitions:
            vals = {
                "name": definition["name"],
                "code": definition["code"],
                "color": 0,
                "is_leave": False,
                "is_unforeseen": False,
                "allow_overlap": True,
                "count_by_days": False,
                "round_days": "HALF",
                "round_days_type": "HALF-UP",
            }
            record = self.sudo().search([("code", "=", definition["code"])], limit=1)
            if record:
                record.write(vals)
            else:
                record = self.sudo().create(vals)

            module_name, xml_name = definition["xmlid"].split(".", 1)
            xmlid = ir_model_data.search([
                ("module", "=", module_name),
                ("name", "=", xml_name),
            ], limit=1)
            xml_vals = {
                "module": module_name,
                "name": xml_name,
                "model": "hr.work.entry.type",
                "res_id": record.id,
                "noupdate": True,
            }
            if xmlid:
                xmlid.write(xml_vals)
            else:
                ir_model_data.create(xml_vals)


# ============================================================
# hr.work.entry — clase única consolidada
# ============================================================
class HrWorkEntry(models.Model):
    _inherit = "hr.work.entry"

    # ----------------------------------------------------------
    # Campos adicionales
    # ----------------------------------------------------------
    pay_period_start    = fields.Date(string="Pago: desde", index=True)
    pay_period_end      = fields.Date(string="Pago: hasta", index=True)
    pay_period_pay_date = fields.Date(string="Pago: fecha", index=True)
    pay_period_label    = fields.Char(string="Pago: quincena", index=True)
    planning_slot_id    = fields.Many2one(
        "planning.slot", string="Turno (Planning)", index=True
    )
    source_work_entry_id = fields.Many2one(
        "hr.work.entry",
        string="Entrada origen recargo",
        index=True,
        copy=False,
    )
    generated_recargo_entry_ids = fields.One2many(
        "hr.work.entry",
        "source_work_entry_id",
        string="Recargos generados",
    )

    def _get_duration_is_valid(self):
        self.ensure_one()
        if self.planning_slot_id and not self.leave_id:
            return False
        return super()._get_duration_is_valid()

    def _normalize_planning_attendance_entries(self):
        for rec in self.filtered(lambda w: w.planning_slot_id and w.planning_slot_id.employee_id == w.employee_id):
            slot = rec.planning_slot_id
            recargo_type_ids = set(slot._get_recargo_rules().mapped("work_entry_type_id").ids)
            if rec.work_entry_type_id.id in recargo_type_ids:
                continue

            start_dt = fields.Datetime.to_datetime(slot.start_datetime)
            end_dt = fields.Datetime.to_datetime(slot.end_datetime)
            if not start_dt or not end_dt or start_dt >= end_dt:
                continue

            expected_duration = (end_dt - start_dt).total_seconds() / 3600.0
            vals = {}
            if rec.leave_id:
                vals["leave_id"] = False
            if rec.date_start != start_dt:
                vals["date_start"] = start_dt
            if rec.date_stop != end_dt:
                vals["date_stop"] = end_dt
            if "duration" in rec._fields and rec.duration != expected_duration:
                vals["duration"] = expected_duration
            if rec.state == "conflict":
                vals["state"] = "draft"

            if vals:
                super(
                    HrWorkEntry,
                    rec.with_context(
                        skip_full_day_leave_normalization=True,
                        skip_worked_time_leave_normalization=True,
                    ).sudo(),
                ).write(vals)

    # ----------------------------------------------------------
    # Helpers TZ
    # ----------------------------------------------------------
    def _get_company_tz_for_entry(self, vals=None):
        company = None
        if vals and vals.get("company_id"):
            company = self.env["res.company"].browse(vals["company_id"])
        if not company and self:
            company = self.company_id
        if not company:
            company = self.env.company

        tz_name = (
            company.resource_calendar_id.tz
            or company.partner_id.tz
            or "UTC"
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _get_employee_tz(self, employee):
        tz_name = (
            getattr(employee, "tz", False)
            or getattr(getattr(employee, "resource_calendar_id", False), "tz", False)
            or getattr(
                getattr(getattr(employee, "company_id", False), "resource_calendar_id", False),
                "tz", False,
            )
            or "UTC"
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _localize_safe(self, tz, dt_naive):
        try:
            return tz.localize(dt_naive, is_dst=None)
        except Exception:
            return tz.localize(dt_naive, is_dst=False)

    def _normalize_date_stop_utc(self, date_stop, vals=None):
        """23:59:00 local → 23:59:59 local (devuelve UTC naive)."""
        if not date_stop:
            return date_stop

        tz = self._get_company_tz_for_entry(vals=vals)

        if isinstance(date_stop, datetime) and date_stop.tzinfo is None:
            stop_aware = pytz.UTC.localize(date_stop)
        else:
            stop_aware = date_stop

        stop_local = stop_aware.astimezone(tz)
        if stop_local.hour == 23 and stop_local.minute == 59 and stop_local.second == 0:
            stop_local = stop_local.replace(second=59, microsecond=0)
            return stop_local.astimezone(pytz.UTC).replace(tzinfo=None)

        return stop_aware.astimezone(pytz.UTC).replace(tzinfo=None)

    def _compute_pay_period_mes_caido(self, work_day):
        self.ensure_one()
        year_value = work_day.year
        month_value = work_day.month
        last_day = calendar.monthrange(year_value, month_value)[1]
        if work_day.day <= 15:
            pay_from = date(year_value, month_value, 16)
            pay_to = date(year_value, month_value, last_day)
        else:
            next_month = month_value + 1
            next_year = year_value
            if next_month == 13:
                next_month = 1
                next_year = year_value + 1
            pay_from = date(next_year, next_month, 1)
            pay_to = date(next_year, next_month, 15)
        pay_date = pay_to
        label = f"{pay_from.strftime('%Y-%m-%d')} a {pay_to.strftime('%Y-%m-%d')}"
        return pay_from, pay_to, pay_date, label

    def _get_recargo_rules_for_company(self, company):
        company = company or self.env.company
        return self.env["payroll.recargo.rule"].sudo().search([
            ("active", "=", True),
            ("company_id", "=", company.id),
        ], order="sequence, id")

    def _get_effective_contract_for_entry(self):
        self.ensure_one()
        if self.contract_id:
            return self.contract_id.sudo()

        employee = self.employee_id.sudo()
        entry_start = fields.Datetime.to_datetime(self.date_start)
        entry_end = fields.Datetime.to_datetime(self.date_stop)
        entry_start_date = entry_start.date() if entry_start else False
        entry_end_date = entry_end.date() if entry_end else entry_start_date

        contract = self.env["hr.contract"]
        contract_ids = getattr(employee, "contract_ids", self.env["hr.contract"]).sudo()
        if contract_ids and entry_start_date:
            matching_contracts = contract_ids.filtered(
                lambda c: (
                    (not c.date_start or c.date_start <= entry_end_date)
                    and (not c.date_end or c.date_end >= entry_start_date)
                )
            ).sorted(
                key=lambda c: (
                    c.date_start or date(1900, 1, 1),
                    c.id,
                ),
                reverse=True,
            )
            open_contracts = matching_contracts.filtered(lambda c: c.state == "open")
            contract = open_contracts[:1] or matching_contracts[:1]

        if not contract:
            current_contract = getattr(employee, "contract_id", False)
            if current_contract:
                contract = current_contract.sudo()

        return contract

    def _get_effective_calendar_for_entry(self):
        self.ensure_one()
        contract = self._get_effective_contract_for_entry()
        return (
            contract.resource_calendar_id
            or self.employee_id.resource_calendar_id
            or self.company_id.resource_calendar_id
        )

    def _get_entry_company_tz(self):
        self.ensure_one()
        tz_name = (
            getattr(self._get_effective_calendar_for_entry(), "tz", False)
            or self.company_id.resource_calendar_id.tz
            or self.company_id.partner_id.tz
            or "UTC"
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _float_to_time(self, hour_float):
        hh = int(hour_float)
        mm = int(round((hour_float - hh) * 60))
        if mm >= 60:
            hh += 1
            mm = 0
        if hh == 24:
            hh = 0
        return time(hh % 24, mm)

    def _rule_applies_to_day(self, rule, cur_day, is_sunday, is_holiday):
        if rule.date_from and cur_day < rule.date_from:
            return False
        if rule.date_to and cur_day > rule.date_to:
            return False
        if is_sunday or is_holiday:
            return bool(
                (is_sunday and rule.apply_on_sunday)
                or (is_holiday and rule.apply_on_holiday)
            )
        return bool(rule.apply_on_normal)

    def _get_weekly_night_shift_limit(self):
        self.ensure_one()
        return max(
            0.0,
            float(getattr(self.company_id, "hr_night_shift_weekly_limit", 0.0) or 0.0),
        )

    def _rule_uses_art_161_weekly_limit(self, rule, contract):
        self.ensure_one()
        return bool(
            rule.apply_art_161_weekly_limit
            and contract
            and getattr(contract, "hr_night_shift_successive", False)
            and self._get_weekly_night_shift_limit() > 0.0
        )

    def _get_calendar_week_local_bounds(self, dt_local):
        self.ensure_one()
        week_start_date = dt_local.date() - timedelta(days=dt_local.weekday())
        week_start = self._localize_safe(
            self._get_entry_company_tz(),
            datetime.combine(week_start_date, time.min),
        )
        week_end = week_start + timedelta(days=7)
        return week_start, week_end

    def _get_weekly_worked_hours_before(self, segment_start_local, recargo_type_ids=None):
        self.ensure_one()
        if not self.employee_id:
            return 0.0

        recargo_type_ids = set(recargo_type_ids or [])
        week_start_local, _week_end_local = self._get_calendar_week_local_bounds(segment_start_local)
        week_start_utc = week_start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        segment_start_utc = segment_start_local.astimezone(pytz.UTC).replace(tzinfo=None)

        work_entries = self.env["hr.work.entry"].sudo().search([
            ("employee_id", "=", self.employee_id.id),
            ("active", "=", True),
            ("leave_id", "=", False),
            ("date_start", "<", segment_start_utc),
            ("date_stop", ">", week_start_utc),
        ])

        total_hours = 0.0
        tz = self._get_entry_company_tz()
        for work_entry in work_entries:
            if work_entry.work_entry_type_id.id in recargo_type_ids:
                continue
            if work_entry.source_work_entry_id:
                continue

            we_start = fields.Datetime.to_datetime(work_entry.date_start)
            we_end = fields.Datetime.to_datetime(work_entry.date_stop)
            if not we_start or not we_end or we_start >= we_end:
                continue

            if we_start.tzinfo is None:
                we_start = pytz.UTC.localize(we_start)
            if we_end.tzinfo is None:
                we_end = pytz.UTC.localize(we_end)

            local_start = we_start.astimezone(tz)
            local_end = we_end.astimezone(tz)
            overlap_start = max(local_start, week_start_local)
            overlap_end = min(local_end, segment_start_local)
            if overlap_start < overlap_end:
                total_hours += (overlap_end - overlap_start).total_seconds() / 3600.0

        return total_hours

    def _apply_art_161_weekly_limit(self, rule, contract, start_local, end_local, recargo_type_ids=None):
        self.ensure_one()
        if not self._rule_uses_art_161_weekly_limit(rule, contract):
            return start_local, end_local

        weekly_limit = self._get_weekly_night_shift_limit()
        worked_hours_before = self._get_weekly_worked_hours_before(
            start_local,
            recargo_type_ids=recargo_type_ids,
        )
        if worked_hours_before >= weekly_limit:
            return start_local, end_local

        exempt_hours_left = weekly_limit - worked_hours_before
        segment_hours = (end_local - start_local).total_seconds() / 3600.0
        if segment_hours <= exempt_hours_left:
            return None, None

        adjusted_start = start_local + timedelta(hours=exempt_hours_left)
        return adjusted_start, end_local

    def _is_recargo_source_candidate(self):
        self.ensure_one()
        if not self.active or self.leave_id or self.source_work_entry_id:
            return False
        if self.planning_slot_id:
            return False
        if not self.employee_id or not self.date_start or not self.date_stop:
            return False
        start_dt = fields.Datetime.to_datetime(self.date_start)
        stop_dt = fields.Datetime.to_datetime(self.date_stop)
        if not start_dt or not stop_dt or start_dt >= stop_dt:
            return False
        recargo_type_ids = self._get_recargo_rules_for_company(self.company_id).mapped("work_entry_type_id").ids
        if self.work_entry_type_id.id in recargo_type_ids:
            return False
        return True

    def _build_expected_recargo_work_entry_vals(self):
        self.ensure_one()
        rules = self._get_recargo_rules_for_company(self.company_id)
        existing = self.generated_recargo_entry_ids.sudo().filtered(lambda we: we.active)

        if not self._is_recargo_source_candidate() or not rules:
            return rules, [], existing

        tz = self._get_entry_company_tz()
        start_utc = fields.Datetime.to_datetime(self.date_start)
        end_utc = fields.Datetime.to_datetime(self.date_stop)
        if not start_utc or not end_utc or start_utc >= end_utc:
            return rules, [], existing

        def to_local(dt_utc):
            if dt_utc.tzinfo is None:
                dt_utc = pytz.UTC.localize(dt_utc)
            return dt_utc.astimezone(tz)

        def day_bounds_local(d_date):
            ds = self._localize_safe(tz, datetime.combine(d_date, time(0, 0, 0)))
            de = self._localize_safe(tz, datetime.combine(d_date, time(23, 59, 59)))
            return ds, de

        def overlap(a1, a2, b1, b2):
            start_dt = max(a1, b1)
            end_dt = min(a2, b2)
            return (start_dt, end_dt) if start_dt < end_dt else (None, None)

        start_local = to_local(start_utc)
        end_local = to_local(end_utc)
        effective_contract = self._get_effective_contract_for_entry()

        if end_local.hour == 23 and end_local.minute == 59 and end_local.second == 0:
            end_local = end_local.replace(second=59)

        cur_day = start_local.date()
        last_day = end_local.date()
        holiday_days = set()

        calendar = self._get_effective_calendar_for_entry()
        if calendar:
            range_start_local = self._localize_safe(tz, datetime.combine(cur_day, time.min))
            range_end_local = self._localize_safe(
                tz,
                datetime.combine(last_day + timedelta(days=1), time.min),
            )
            leaves = self.env["resource.calendar.leaves"].sudo().search([
                ("calendar_id", "=", calendar.id),
                ("resource_id", "=", False),
                ("date_from", "<", range_end_local.astimezone(pytz.UTC).replace(tzinfo=None)),
                ("date_to", ">", range_start_local.astimezone(pytz.UTC).replace(tzinfo=None)),
            ])
            for leave in leaves:
                leave_start = to_local(fields.Datetime.to_datetime(leave.date_from))
                leave_end = to_local(fields.Datetime.to_datetime(leave.date_to))
                day_cursor = leave_start.date()
                day_end = (leave_end - timedelta(seconds=1)).date()
                while day_cursor <= day_end:
                    holiday_days.add(day_cursor)
                    day_cursor += timedelta(days=1)

        if "hr.holidays.public.line" in self.env:
            public_holidays = self.env["hr.holidays.public.line"].sudo().search([
                ("date", ">=", cur_day),
                ("date", "<=", last_day),
            ])
            for holiday in public_holidays:
                hol_date = holiday.date
                if isinstance(hol_date, str):
                    hol_date = fields.Date.to_date(hol_date)
                holiday_days.add(hol_date)

        recargo_type_ids = rules.mapped("work_entry_type_id").ids
        raw_vals = []
        while cur_day <= last_day:
            day_start, day_end = day_bounds_local(cur_day)
            seg_start_local = max(start_local, day_start)
            seg_end_local = min(end_local, day_end)

            if seg_start_local >= seg_end_local:
                cur_day += timedelta(days=1)
                continue

            is_sunday = cur_day.weekday() == 6
            is_holiday = cur_day in holiday_days

            for rule in rules:
                if not self._rule_applies_to_day(rule, cur_day, is_sunday, is_holiday):
                    continue

                rule_start_time = self._float_to_time(rule.hour_from)
                rule_start = self._localize_safe(tz, datetime.combine(cur_day, rule_start_time))

                if rule.hour_to == 24.0:
                    rule_end = self._localize_safe(
                        tz,
                        datetime.combine(cur_day, time(23, 59, 59)),
                    )
                else:
                    rule_end_time = self._float_to_time(rule.hour_to)
                    rule_end = self._localize_safe(tz, datetime.combine(cur_day, rule_end_time))
                    if rule_end <= rule_start:
                        rule_end = self._localize_safe(
                            tz,
                            datetime.combine(cur_day + timedelta(days=1), rule_end_time),
                        )

                segment_start, segment_end = overlap(
                    seg_start_local,
                    seg_end_local,
                    rule_start,
                    rule_end,
                )
                if not segment_start or not segment_end:
                    continue

                if (is_sunday or is_holiday) and rule.apply_on_normal:
                    continue

                if (
                    segment_end.hour == 23
                    and segment_end.minute == 59
                    and segment_end.second == 0
                ):
                    segment_end = segment_end.replace(second=59)

                segment_start, segment_end = self._apply_art_161_weekly_limit(
                    rule,
                    effective_contract,
                    segment_start,
                    segment_end,
                    recargo_type_ids=recargo_type_ids,
                )
                if not segment_start or not segment_end:
                    continue

                work_day = segment_start.date()
                pay_from, pay_to, pay_date, pay_label = self._compute_pay_period_mes_caido(work_day)
                raw_vals.append({
                    "name": rule.work_entry_type_id.name,
                    "employee_id": self.employee_id.id,
                    "work_entry_type_id": rule.work_entry_type_id.id,
                    "contract_id": effective_contract.id if effective_contract else False,
                    "date_start": segment_start.astimezone(pytz.UTC).replace(tzinfo=None),
                    "date_stop": segment_end.astimezone(pytz.UTC).replace(tzinfo=None),
                    "source_work_entry_id": self.id,
                    "state": "draft",
                    "company_id": self.company_id.id,
                    "duration": (segment_end - segment_start).total_seconds() / 3600.0,
                    "pay_period_start": pay_from,
                    "pay_period_end": pay_to,
                    "pay_period_pay_date": pay_date,
                    "pay_period_label": pay_label,
                })

            cur_day += timedelta(days=1)

        dedup_map = {}
        for vals in raw_vals:
            key = (
                vals["employee_id"],
                vals["work_entry_type_id"],
                vals["date_start"],
                vals["date_stop"],
                vals["source_work_entry_id"],
            )
            dedup_map[key] = vals
        return rules, list(dedup_map.values()), existing

    def _sync_generated_recargo_work_entries(self):
        work_entry_model = self.env["hr.work.entry"].sudo()
        for entry in self:
            rules, expected_vals, existing = entry._build_expected_recargo_work_entry_vals()
            type_ids = rules.mapped("work_entry_type_id").ids

            if not type_ids:
                if existing:
                    existing._soft_remove_entries()
                continue

            if not existing:
                existing = work_entry_model.search([
                    ("source_work_entry_id", "=", entry.id),
                    ("work_entry_type_id", "in", type_ids),
                    ("active", "=", True),
                ], order="date_start asc, id asc")

            def key_from_vals(vals):
                return (
                    vals["employee_id"],
                    vals["work_entry_type_id"],
                    fields.Datetime.to_datetime(vals["date_start"]),
                    fields.Datetime.to_datetime(vals["date_stop"]),
                    vals["source_work_entry_id"],
                )

            def key_from_we(work_entry):
                return (
                    work_entry.employee_id.id,
                    work_entry.work_entry_type_id.id,
                    fields.Datetime.to_datetime(work_entry.date_start),
                    fields.Datetime.to_datetime(work_entry.date_stop),
                    work_entry.source_work_entry_id.id,
                )

            expected_map = {key_from_vals(vals): vals for vals in expected_vals}
            grouped_existing = {}
            for work_entry in existing:
                grouped_existing.setdefault(key_from_we(work_entry), work_entry_model.browse())
                grouped_existing[key_from_we(work_entry)] |= work_entry

            to_remove = work_entry_model.browse()
            missing_vals = []

            for key, entries in grouped_existing.items():
                expected = expected_map.get(key)
                if not expected:
                    to_remove |= entries
                    continue

                survivor = entries[0]
                vals = {}
                if survivor.state == "conflict":
                    vals["state"] = "draft"
                if "duration" in survivor._fields and survivor.duration != expected["duration"]:
                    vals["duration"] = expected["duration"]
                if vals:
                    survivor.with_context(
                        skip_full_day_leave_normalization=True,
                        skip_worked_time_leave_normalization=True,
                        skip_generated_recargo_sync=True,
                    ).sudo().write(vals)

                duplicates = entries - survivor
                if duplicates:
                    to_remove |= duplicates

            for key, vals in expected_map.items():
                if key not in grouped_existing:
                    missing_vals.append(vals)

            if to_remove:
                to_remove.with_context(skip_generated_recargo_sync=True)._soft_remove_entries()
            if missing_vals:
                work_entry_model.with_context(skip_generated_recargo_sync=True).create(missing_vals)

    def _sync_generated_recargo_work_entries_for_range(self, employee_ids, dt_from, dt_to):
        if not employee_ids or not dt_from or not dt_to:
            return
        entries = self.env["hr.work.entry"].sudo().search([
            ("employee_id", "in", employee_ids),
            ("active", "=", True),
            ("leave_id", "=", False),
            ("source_work_entry_id", "=", False),
            ("planning_slot_id", "=", False),
            ("date_start", "<", dt_to),
            ("date_stop", ">", dt_from),
        ])
        entries._sync_generated_recargo_work_entries()

    # ----------------------------------------------------------
    # Conflictos: respetar allow_overlap
    # ----------------------------------------------------------
    def _mark_conflicting_work_entries(self, start, stop):
        """
        Marca estado 'conflict' en entradas solapadas.
        Si al menos una tiene allow_overlap=True, NO se marca conflicto.
        """
        self.flush_model(["date_start", "date_stop", "employee_id", "active", "work_entry_type_id"])
        self.env["hr.work.entry.type"].flush_model(["allow_overlap"])
        self.env["hr.leave"].flush_model(["holiday_status_id"])
        self.env["hr.leave.type"].flush_model(["time_type"])

        extra_domain = (
            "b2.id IN %(ids)s"
            if self.ids
            else "b2.date_start <= %(stop)s AND b2.date_stop >= %(start)s"
        )

        query = f"""
            SELECT b1.id, b2.id
              FROM hr_work_entry b1
              JOIN hr_work_entry b2
                ON b1.employee_id = b2.employee_id
               AND b1.id <> b2.id
              LEFT JOIN hr_work_entry_type t1 ON t1.id = b1.work_entry_type_id
              LEFT JOIN hr_work_entry_type t2 ON t2.id = b2.work_entry_type_id
              LEFT JOIN hr_leave l1 ON l1.id = b1.leave_id
              LEFT JOIN hr_leave l2 ON l2.id = b2.leave_id
              LEFT JOIN hr_leave_type lt1 ON lt1.id = l1.holiday_status_id
              LEFT JOIN hr_leave_type lt2 ON lt2.id = l2.holiday_status_id
             WHERE b1.date_start <= %(stop)s
               AND b1.date_stop  >= %(start)s
               AND b1.active = TRUE
               AND b2.active = TRUE
               AND tsrange(b1.date_start, b1.date_stop, '()')
                   && tsrange(b2.date_start, b2.date_stop, '()')
               AND NOT (
                     COALESCE(t1.allow_overlap, FALSE) = TRUE
                  OR COALESCE(t2.allow_overlap, FALSE) = TRUE
                  OR COALESCE(lt1.time_type, '') = 'other'
                  OR COALESCE(lt2.time_type, '') = 'other'
               )
               AND {extra_domain}
        """
        params = {
            "stop": stop,
            "start": start,
            "ids": tuple(self.ids) if self.ids else tuple(),
        }
        self.env.cr.execute(query, params)
        conflicts = set(itertools.chain.from_iterable(self.env.cr.fetchall()))
        if conflicts:
            self.browse(conflicts).write({"state": "conflict"})
        return bool(conflicts)

    # ----------------------------------------------------------
    # Detección de ausencias reales del empleado (a preservar)
    # ----------------------------------------------------------
    def _is_employee_requested_absence(self, rec):
        """
        True si la WE viene de una ausencia personal del empleado
        (incapacidad, vacaciones, permiso remunerado, etc.).
        Estas deben preservarse aunque haya planeación.

        False para festivos de calendario público (Reyes Magos, Año Nuevo, etc.),
        tanto si tienen leave_id como si no, ya que son compañía/global.
        """
        if not rec.leave_id:
            # Sin leave_id: WE del contrato/calendario → se puede eliminar
            return False

        leave = rec.leave_id

        # En Odoo, holiday_type='employee' son ausencias personales del empleado
        holiday_type = getattr(leave, "holiday_type", None)

        if holiday_type == "employee":
            return True  # Ausencia personal → preservar

        if holiday_type in ("company", "department", "category"):
            return False  # Festivo/ausencia colectiva → se puede eliminar

        # holiday_type desconocido o None: decidir por employee_id
        # Si el leave tiene employee_id propio y coincide → preservar
        if holiday_type is None and leave.employee_id and leave.employee_id == rec.employee_id:
            return True

        # Por defecto: se puede eliminar
        return False

    # ----------------------------------------------------------
    # Limpieza de WEs de festivos/calendario en días con planeación
    # ----------------------------------------------------------
    def _cleanup_leave_entries_conflicting_with_slots(self):
        """
        Regla de negocio:
            Si un día tiene un turno planificado para el empleado, solo
            deben quedar las WEs del planning slot.  Las WEs autogeneradas
            por el sistema (festivos, contrato, calendar.leaves) para ese
            día se eliminan.

        ESTADOS cubiertos: draft Y conflict.
            En Odoo 18, _check_if_error() puede marcar la WE como 'conflict'
            DENTRO del mismo create() antes de que nuestro post-create corra.
            Por eso filtramos ambos estados.

        BÚSQUEDA por DÍA LOCAL (no por solapamiento de horas):
            El festivo puede estar en un horario distinto al del slot
            (ej: festivo 08:00-16:00 vs slots 00:00-06:00 y 22:00-23:59).
            Buscamos cualquier planning.slot en el mismo día del empleado.

        Se preservan ausencias personales del empleado (incapacidad,
        vacaciones, permisos con holiday_type='employee').
        """
        # Solo procesar WEs que NO son de planning slot
        candidates = self.filtered(lambda w: not w.planning_slot_id)
        if not candidates:
            return

        to_unlink = self.env["hr.work.entry"]

        for rec in candidates:
            if not rec.date_start or not rec.date_stop:
                continue

            # DRAFT, CONFLICT y VALIDATED: todos son elegibles para limpieza
            if rec.state not in ("draft", "conflict", "validated"):
                continue

            # Preservar ausencias personales del empleado
            if self._is_employee_requested_absence(rec):
                _logger.debug(
                    "[FESTIVO CLEANUP] Preservando WE id=%s (ausencia personal emp=%s leave_id=%s)",
                    rec.id, rec.employee_id.name, rec.leave_id.id if rec.leave_id else "none",
                )
                continue

            # Convertir date_start a fecha local del empleado
            tz = self._get_employee_tz(rec.employee_id)
            date_start_dt = rec.date_start
            if isinstance(date_start_dt, datetime):
                date_start_aware = (
                    pytz.UTC.localize(date_start_dt)
                    if date_start_dt.tzinfo is None
                    else date_start_dt
                )
            else:
                # Por si acaso date_start es date en vez de datetime
                date_start_aware = pytz.UTC.localize(
                    datetime.combine(date_start_dt, time.min)
                )

            local_date = date_start_aware.astimezone(tz).date()

            # Rango UTC que cubre el día local completo (00:00 → siguiente 00:00)
            day_start_utc = tz.localize(
                datetime.combine(local_date, time.min)
            ).astimezone(pytz.UTC).replace(tzinfo=None)

            day_end_utc = tz.localize(
                datetime.combine(local_date + timedelta(days=1), time.min)
            ).astimezone(pytz.UTC).replace(tzinfo=None)

            # Existe algún planning slot NO descanso para ese empleado en ese día?
            planning_slot = self.env["planning.slot"].sudo().search([
                ("employee_id",    "=", rec.employee_id.id),
                ("is_rest_day",    "=", False),
                ("start_datetime", "<", day_end_utc),
                ("end_datetime",   ">", day_start_utc),
            ], limit=1)

            if planning_slot:
                _logger.info(
                    "[FESTIVO CLEANUP] Eliminando WE id=%s tipo=%s emp=%s fecha=%s "
                    "state=%s — slot id=%s en ese día (leave_id=%s).",
                    rec.id,
                    rec.work_entry_type_id.code or rec.work_entry_type_id.name,
                    rec.employee_id.name,
                    local_date,
                    rec.state,
                    planning_slot.id,
                    rec.leave_id.id if rec.leave_id else "none",
                )
                to_unlink |= rec
            else:
                _logger.debug(
                    "[FESTIVO CLEANUP] WE id=%s emp=%s fecha=%s — sin slot ese día, preservando.",
                    rec.id, rec.employee_id.name, local_date,
                )

        if to_unlink:
            removed_scope = {
                "employee_ids": to_unlink.mapped("employee_id").ids,
                "starts": [dt for dt in to_unlink.mapped("date_start") if dt],
                "stops": [dt for dt in to_unlink.mapped("date_stop") if dt],
            }
            # Forzar draft antes de eliminar por si están validadas o en conflicto
            to_unlink._soft_remove_entries()
            self._recheck_conflicts_after_cleanup(removed_scope)

    def _recheck_conflicts_after_cleanup(self, removed_scope):
        """
        Después de eliminar WEs de festivo/calendario, recalcula conflictos
        porque algunas WEs quedan pegadas en state='conflict' aunque ya no
        exista la contraparte que generó el choque.
        """
        if not removed_scope:
            return

        employees = removed_scope.get("employee_ids") or []
        starts = removed_scope.get("starts") or []
        stops = removed_scope.get("stops") or []
        if not employees or not starts or not stops:
            return

        remaining = self.env["hr.work.entry"].sudo().search([
            ("employee_id", "in", employees),
            ("date_start", "<=", max(stops)),
            ("date_stop", ">=", min(starts)),
            ("state", "=", "conflict"),
            ("active", "=", True),
        ])
        if not remaining:
            return

        remaining._reset_conflicting_state()
        remaining._check_if_error()
        remaining._clear_false_conflicts()

    def _clear_false_conflicts(self):
        """
        Limpia estados conflict residuales cuando ya no existe un choque real
        según las reglas actuales de allow_overlap / Worked Time.
        """
        conflict_entries = self.filtered(lambda w: w.active and w.state == "conflict")
        if not conflict_entries:
            return

        self.flush_model(["date_start", "date_stop", "employee_id", "active", "work_entry_type_id"])
        self.env["hr.work.entry.type"].flush_model(["allow_overlap"])
        self.env["hr.leave"].flush_model(["holiday_status_id"])
        self.env["hr.leave.type"].flush_model(["time_type"])

        query = """
            SELECT DISTINCT b2.id
              FROM hr_work_entry b1
              JOIN hr_work_entry b2
                ON b1.employee_id = b2.employee_id
               AND b1.id <> b2.id
              LEFT JOIN hr_work_entry_type t1 ON t1.id = b1.work_entry_type_id
              LEFT JOIN hr_work_entry_type t2 ON t2.id = b2.work_entry_type_id
              LEFT JOIN hr_leave l1 ON l1.id = b1.leave_id
              LEFT JOIN hr_leave l2 ON l2.id = b2.leave_id
              LEFT JOIN hr_leave_type lt1 ON lt1.id = l1.holiday_status_id
              LEFT JOIN hr_leave_type lt2 ON lt2.id = l2.holiday_status_id
             WHERE b1.active = TRUE
               AND b2.active = TRUE
               AND b2.id IN %(ids)s
               AND tsrange(b1.date_start, b1.date_stop, '()')
                   && tsrange(b2.date_start, b2.date_stop, '()')
               AND NOT (
                     COALESCE(t1.allow_overlap, FALSE) = TRUE
                  OR COALESCE(t2.allow_overlap, FALSE) = TRUE
                  OR COALESCE(lt1.time_type, '') = 'other'
                  OR COALESCE(lt2.time_type, '') = 'other'
               )
        """
        self.env.cr.execute(query, {"ids": tuple(conflict_entries.ids)})
        real_conflicts = {row[0] for row in self.env.cr.fetchall()}
        false_conflicts = conflict_entries.filtered(lambda w: w.id not in real_conflicts)
        if false_conflicts:
            false_conflicts.with_context(
                skip_worked_time_leave_normalization=True,
                skip_full_day_leave_normalization=True,
            ).write({"state": "draft"})

    def _is_public_holiday_day(self, employee, local_date):
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if calendar:
            tz = self._get_employee_tz(employee)
            start_utc = tz.localize(datetime.combine(local_date, time.min)).astimezone(pytz.UTC).replace(tzinfo=None)
            stop_utc = tz.localize(datetime.combine(local_date + timedelta(days=1), time.min)).astimezone(pytz.UTC).replace(tzinfo=None)
            leave = self.env["resource.calendar.leaves"].sudo().search([
                ("calendar_id", "=", calendar.id),
                ("resource_id", "=", False),
                ("date_from", "<", stop_utc),
                ("date_to", ">", start_utc),
            ], limit=1)
            if leave:
                return True

        if "hr.holidays.public.line" in self.env:
            hol = self.env["hr.holidays.public.line"].sudo().search([("date", "=", local_date)], limit=1)
            if hol:
                return True
        return False

    def _match_worked_time_leave_for_entry(self, rec):
        """
        Algunos flujos de Odoo generan la WE del permiso por horas como
        WORK100 sin leave_id. Intentamos vincularla al leave "Worked Time"
        correcto usando empleado y solapamiento horario.
        """
        if not rec.employee_id or not rec.date_start or not rec.date_stop:
            return self.env["hr.leave"]

        candidates = self.env["hr.leave"].sudo().search([
            ("employee_id", "=", rec.employee_id.id),
            ("date_from", "<", rec.date_stop),
            ("date_to", ">", rec.date_start),
            ("holiday_status_id.time_type", "=", "other"),
            ("state", "in", ["confirm", "validate"]),
        ], order="date_from desc, id desc")
        if not candidates:
            return self.env["hr.leave"]

        exact = candidates.filtered(
            lambda l: l.date_from == rec.date_start and l.date_to == rec.date_stop
        )
        if exact:
            return exact[:1]

        contained = candidates.filtered(
            lambda l: l.date_from <= rec.date_start and l.date_to >= rec.date_stop
        )
        if contained:
            return contained[:1]

        return candidates[:1]

    def _soft_remove_entries(self):
        if not self:
            return
        non_draft = self.filtered(lambda w: "state" in w._fields and w.state != "draft")
        if non_draft:
            non_draft.sudo().write({"state": "draft"})
        if "active" in self._fields:
            self.sudo().write({"active": False})
        else:
            self.sudo().unlink()

    def _resolve_overtime_code_from_leave_type(self, leave_type, is_special):
        configured_type = (
            leave_type.work_entry_type_id.sudo()
            if leave_type and leave_type.work_entry_type_id
            else self.env["hr.work.entry.type"]
        )
        configured_code = ((configured_type.code or "") if configured_type else "").strip().upper()
        mapping = {"HED": "HEDDF", "HEN": "HENDF"}
        overtime_codes = {"HED", "HEN", "HEDDF", "HENDF"}

        raw_name = " ".join(
            filter(
                None,
                [
                    getattr(leave_type, "name", False),
                    getattr(leave_type, "display_name", False),
                    configured_type.name if configured_type else False,
                ],
            )
        ).lower()

        if "diurna" in raw_name:
            return ("HEDDF" if is_special else "HED"), configured_type
        if "nocturna" in raw_name:
            return ("HENDF" if is_special else "HEN"), configured_type
        if configured_code not in overtime_codes:
            return configured_code, configured_type
        if is_special and configured_code in mapping:
            return mapping[configured_code], configured_type
        if not is_special and configured_code in mapping.values():
            reverse_mapping = {value: key for key, value in mapping.items()}
            return reverse_mapping.get(configured_code, configured_code), configured_type
        return configured_code, configured_type

    def _normalize_worked_time_leave_entries(self):
        """
        Ajusta work entries originadas por leaves de tipo Worked Time:
        - remapea a tipo festivo/dominical si corresponde
        - permite solapamiento para evitar conflictos con asistencia/festivo
        """
        if self.env.context.get("skip_worked_time_leave_normalization"):
            return

        overtime_codes = {"HED", "HEN", "HEDDF", "HENDF"}
        touched_scope = []

        for rec in self.filtered(lambda w: w.work_entry_type_id and not w.planning_slot_id):
            leave = rec.leave_id or self._match_worked_time_leave_for_entry(rec)
            leave_type = leave.holiday_status_id
            if not leave_type or leave_type.time_type != "other":
                continue

            tz = self._get_employee_tz(rec.employee_id)
            local_start = pytz.UTC.localize(rec.date_start).astimezone(tz) if rec.date_start and rec.date_start.tzinfo is None else rec.date_start.astimezone(tz)
            local_date = local_start.date() if local_start else False
            is_special = bool(local_date and (local_date.weekday() == 6 or self._is_public_holiday_day(rec.employee_id, local_date)))
            target_code, configured_type = self._resolve_overtime_code_from_leave_type(leave_type, is_special)
            if target_code not in overtime_codes:
                continue

            target_type = self.env["hr.work.entry.type"].sudo().search([("code", "=", target_code)], limit=1)
            if not target_type:
                target_type = configured_type

            if target_type and not target_type.allow_overlap:
                target_type.write({"allow_overlap": True})

            vals = {}
            if leave and rec.leave_id.id != leave.id:
                vals["leave_id"] = leave.id
            if target_type and rec.work_entry_type_id.id != target_type.id:
                vals["work_entry_type_id"] = target_type.id

            requested_hours = max(0.0, float(leave.request_hour_to or 0.0) - float(leave.request_hour_from or 0.0))
            if requested_hours and rec.duration != requested_hours:
                vals["duration"] = requested_hours
                if rec.date_start:
                    vals["date_stop"] = rec.date_start + timedelta(hours=requested_hours)

            if vals:
                super(HrWorkEntry, rec.sudo()).write(vals)
                touched_scope.append((
                    rec.employee_id.id,
                    vals.get("date_start", rec.date_start),
                    vals.get("date_stop", rec.date_stop),
                ))

        if touched_scope:
            employee_ids = list({employee_id for employee_id, _start, _stop in touched_scope if employee_id})
            starts = [start for _employee_id, start, _stop in touched_scope if start]
            stops = [stop for _employee_id, _start, stop in touched_scope if stop]
            if employee_ids and starts and stops:
                impacted = self.env["hr.work.entry"].sudo().search([
                    ("employee_id", "in", employee_ids),
                    ("date_start", "<=", max(stops)),
                    ("date_stop", ">=", min(starts)),
                    ("active", "=", True),
                ])
                if impacted:
                    impacted.filtered(lambda w: w.state == "conflict")._reset_conflicting_state()
                    impacted._check_if_error()
                    impacted._clear_false_conflicts()

    # ----------------------------------------------------------
    # Normalización ausencias día completo
    # ----------------------------------------------------------
    def _get_leave_full_day_tz(self, leave):
        tz_name = (
            getattr(leave.employee_id, "tz", False)
            or getattr(getattr(leave.employee_id, "resource_calendar_id", False), "tz", False)
            or getattr(getattr(leave.company_id, "resource_calendar_id", False), "tz", False)
            or "UTC"
        )
        return pytz.timezone(tz_name)

    def _get_full_day_range_from_leave(self, leave):
        tz = self._get_leave_full_day_tz(leave)
        start_local = datetime.combine(leave.request_date_from, time(0, 0, 0))
        stop_local  = datetime.combine(leave.request_date_to,   time(23, 59, 59))
        start_utc = tz.localize(start_local).astimezone(pytz.UTC).replace(tzinfo=None)
        stop_utc  = tz.localize(stop_local).astimezone(pytz.UTC).replace(tzinfo=None)
        return start_utc, stop_utc

    def _get_full_day_duration_from_leave(self, leave):
        if not leave.request_date_from or not leave.request_date_to:
            return 0.0
        total_days = (leave.request_date_to - leave.request_date_from).days + 1
        return float(total_days * 24)

    def _normalize_full_day_leave_entries(self):
        """
        Ajusta WEs full_day_auto a 00:00:00-23:59:59 local y consolida
        duplicados del mismo leave en una sola WE.
        """
        if self.env.context.get("skip_full_day_leave_normalization"):
            return

        grouped = defaultdict(lambda: self.env["hr.work.entry"])

        for rec in self:
            leave = rec.leave_id
            if not leave:
                continue
            if not leave.holiday_status_id or not leave.holiday_status_id.full_day_auto:
                continue
            if not leave.request_date_from or not leave.request_date_to:
                continue

            grouped[(leave.id, rec.employee_id.id, rec.work_entry_type_id.id, rec.company_id.id)] |= rec

        for leave_id, employee_id, work_entry_type_id, company_id in grouped:
            leave = self.env["hr.leave"].sudo().browse(leave_id)
            if not leave.exists():
                continue

            entries = self.env["hr.work.entry"].sudo().search([
                ("leave_id", "=", leave_id),
                ("employee_id", "=", employee_id),
                ("work_entry_type_id", "=", work_entry_type_id),
                ("company_id", "=", company_id),
            ], order="date_start asc, id asc")
            if not entries:
                continue

            new_start, new_stop = self._get_full_day_range_from_leave(leave)
            new_duration = self._get_full_day_duration_from_leave(leave)

            survivor = entries[0]
            vals = {}
            if survivor.date_start != new_start:
                vals["date_start"] = new_start
            if survivor.date_stop != new_stop:
                vals["date_stop"] = new_stop
            if "duration" in survivor._fields and survivor.duration != new_duration:
                vals["duration"] = new_duration

            if vals:
                super(
                    HrWorkEntry,
                    survivor.with_context(skip_full_day_leave_normalization=True).sudo(),
                ).write(vals)

            duplicates = entries - survivor
            if duplicates:
                duplicates._soft_remove_entries()

    # ----------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # 1. Normalizar date_stop 23:59:00 → 23:59:59
        new_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("date_stop"):
                stop_dt = fields.Datetime.to_datetime(vals["date_stop"])
                if stop_dt:
                    vals["date_stop"] = self._normalize_date_stop_utc(stop_dt, vals=vals)
            new_vals_list.append(vals)

        records = super().create(new_vals_list)

        # 2. Ajustar ausencias full_day_auto
        if not self.env.context.get("skip_full_day_leave_normalization"):
            records._normalize_full_day_leave_entries()
        if not self.env.context.get("skip_worked_time_leave_normalization"):
            records._normalize_worked_time_leave_entries()
        records._normalize_planning_attendance_entries()

        # 3. Eliminar WEs de festivos/calendario en días con planeación.
        #    Cubre estados 'draft' Y 'conflict' porque Odoo 18 puede marcar
        #    conflictos dentro del mismo create() antes de que lleguemos aquí.
        records._cleanup_leave_entries_conflicting_with_slots()
        if not self.env.context.get("skip_generated_recargo_sync"):
            records._sync_generated_recargo_work_entries()

        return records

    def write(self, vals):
        vals = dict(vals)
        if vals.get("date_stop"):
            stop_dt = fields.Datetime.to_datetime(vals["date_stop"])
            if stop_dt:
                vals["date_stop"] = self._normalize_date_stop_utc(stop_dt, vals=vals)

        res = super().write(vals)
        if not self.env.context.get("skip_full_day_leave_normalization"):
            self._normalize_full_day_leave_entries()
        if not self.env.context.get("skip_worked_time_leave_normalization"):
            self._normalize_worked_time_leave_entries()
        self._normalize_planning_attendance_entries()
        if not self.env.context.get("skip_generated_recargo_sync"):
            self._sync_generated_recargo_work_entries()
        return res

    def unlink(self):
        generated = self.sudo().mapped("generated_recargo_entry_ids").filtered(lambda we: we.active)
        if generated:
            generated.with_context(skip_generated_recargo_sync=True)._soft_remove_entries()
        return super().unlink()


# ============================================================
# hr.leave.type — campo full_day_auto
# ============================================================
class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    full_day_auto = fields.Boolean(
        string="Forzar día completo (00:00:00 - 23:59:59)",
        help=(
            "Si está activo, las entradas de trabajo generadas por esta "
            "ausencia se ajustarán automáticamente al día completo."
        ),
    )


# ============================================================
# planning.slot.template — código e indicador de descanso
# ============================================================
class PlanningSlotTemplate(models.Model):
    _inherit = "planning.slot.template"

    code = fields.Char(string="Código", help="Ej: M, T, N, D, DESEA", copy=False)
    is_rest_template = fields.Boolean(
        string="Plantilla de descanso",
        help="Si está activado, representa un día/periodo de descanso.",
    )

    _sql_constraints = [
        (
            "planning_slot_template_code_unique",
            "unique(code)",
            "El código del turno debe ser único.",
        ),
    ]
