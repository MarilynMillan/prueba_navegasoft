# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import time, datetime, timedelta
import pytz
import calendar
import logging

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de tiempo
# ---------------------------------------------------------------------------

def _time_in_window(local_dt, start_t, end_t, inclusive_end=False):
    """
    True si la HORA local de local_dt cae en la ventana configurada.

    Regla base:
    - límite inferior inclusivo
    - límite superior exclusivo

    Si inclusive_end=True, el límite superior también entra.

    Soporta ventanas que cruzan medianoche.
    """
    if not local_dt or start_t is None or end_t is None:
        return False

    if isinstance(local_dt, datetime):
        lt = local_dt.timetz().replace(tzinfo=None)
    else:
        lt = local_dt

    # Ventana normal
    if start_t <= end_t:
        if inclusive_end:
            return start_t <= lt <= end_t
        return start_t <= lt < end_t

    # Ventana cruzando medianoche
    if inclusive_end:
        return (lt >= start_t) or (lt <= end_t)
    return (lt >= start_t) or (lt < end_t)


def _as_local(dt, tzname):
    """
    Convierte datetime UTC/naive a datetime aware en tzname.
    """
    if not dt:
        return False
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(pytz.timezone(tzname))


def _local_day_bounds(date_obj, tzname):
    tz = pytz.timezone(tzname)
    start_local = tz.localize(datetime.combine(date_obj, time.min))
    end_local = tz.localize(datetime.combine(date_obj, time.max))
    return start_local, end_local


def _local_bounds_to_utc(start_local, end_local):
    return (
        start_local.astimezone(pytz.UTC).replace(tzinfo=None),
        end_local.astimezone(pytz.UTC).replace(tzinfo=None),
    )


# ---------------------------------------------------------------------------
# hr.salary.rule
# ---------------------------------------------------------------------------
class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @staticmethod
    def _payroll_rules_planning_rule_xmlids():
        return {
            "MOB": "payroll_rules_planning.rule_bono_movilidad",
            "ROD": "payroll_rules_planning.rule_aux_rodamiento",
            "HRN": "payroll_rules_planning.rule_recargo_nocturno",
            "HRNDF": "payroll_rules_planning.rule_recargo_nocturno_fest",
            "HRDDF": "payroll_rules_planning.rule_recargo_diurno_dom",
        }

    @api.model
    def sync_payroll_rules_planning_salary_rules(self):
        xmlids_by_code = self._payroll_rules_planning_rule_xmlids()
        for code, xmlid in xmlids_by_code.items():
            canonical_rule = self.env.ref(xmlid, raise_if_not_found=False)
            if not canonical_rule:
                continue
            canonical_rule = canonical_rule.sudo()
            if not canonical_rule.active:
                canonical_rule.write({"active": True})

            duplicate_rules = self.sudo().search([
                ("code", "=", code),
                ("id", "!=", canonical_rule.id),
                ("active", "=", True),
            ])
            if duplicate_rules:
                _logger.info(
                    "[PAYROLL RULE SYNC] Deactivating duplicate salary rules for code %s: %s",
                    code,
                    duplicate_rules.ids,
                )
                duplicate_rules.write({"active": False})


# ---------------------------------------------------------------------------
# hr.payslip
# ---------------------------------------------------------------------------
class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # ==========================
    # Lectura de configuración
    # ==========================
    def _company_get(self, employee):
        return employee.company_id or self.env.company

    def _company_tz(self, employee):
        if getattr(employee, "tz", False):
            return employee.tz
        cal = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        return (cal.tz or "UTC") if cal else "UTC"

    def _get_home_office_codes(self, company):
        raw = (company.hr_bonus_home_office_codes or "HOME,REMOTE") if company else "HOME,REMOTE"
        return [c.strip().upper() for c in raw.split(",") if c and c.strip()]

    def _get_holiday_codes(self, company):
        raw = (company.hr_bonus_holiday_we_type_codes or "PUBLIC,PH,FEST") if company else "PUBLIC,PH,FEST"
        return [c.strip().upper() for c in raw.split(",") if c and c.strip()]

    def _defer_to_next_quincena(self, company):
        return bool(company and company.hr_bonus_defer_to_next_quincena)

    # ==========================
    # Utilidades base
    # ==========================
    def _float_to_time(self, hour_float):
        if hour_float is None:
            return time(0, 0)

        hh = int(hour_float)
        mm = int(round((hour_float - hh) * 60))
        if mm >= 60:
            hh += 1
            mm = 0
        if hh == 24:
            hh = 0
        return time(hh % 24, mm)

    def _entry_is_home_office(self, work_entry, employee):
        company = self._company_get(employee)
        codes = set(self._get_home_office_codes(company))
        code = (work_entry.work_entry_type_id.code or "").strip().upper() if work_entry.work_entry_type_id else ""
        return bool(code in codes)

    def _entry_is_bonus_base_work(self, work_entry):
        """
        Solo considerar entradas base de asistencia para movilidad/rodamiento.
        Excluye recargos y otros tipos.
        """
        wet = work_entry.work_entry_type_id
        code = (wet.code or "").strip().upper() if wet else ""

        allowed_codes = {
            "WORK100",
            "WORK",
            "ATTENDANCE",
            "ASISTENCIA",
        }

        if code in allowed_codes:
            return True

        if code.startswith("WORK"):
            return True

        # fallback por nombre
        name = (wet.name or "").strip().upper() if wet else ""
        if "ASISTENCIA" in name:
            return True

        return False

    def _search_work_entries_localized(self, employee, date_from, date_to):
        tzname = self._company_tz(employee)
        start_loc_from, end_loc_from = _local_day_bounds(date_from, tzname)
        start_loc_to, end_loc_to = _local_day_bounds(date_to, tzname)

        start_utc, _ = _local_bounds_to_utc(start_loc_from, end_loc_from)
        _, end_utc = _local_bounds_to_utc(start_loc_to, end_loc_to)

        entries = self.env["hr.work.entry"].search([
            ("employee_id", "=", employee.id),
            ("date_start", "<=", end_utc),
            ("date_stop", ">=", start_utc),
        ], order="date_start asc")

        _logger.info(
            "[BONUS SEARCH] employee=%s range=%s..%s found_entries=%s",
            employee.name, date_from, date_to, entries.ids
        )
        return entries

    def _get_bonus_candidate_entries(self, employee, date_from, date_to):
        entries = self._search_work_entries_localized(employee, date_from, date_to)
        result = self.env["hr.work.entry"]

        for we in entries:
            code = (we.work_entry_type_id.code or "").strip().upper() if we.work_entry_type_id else ""
            name = (we.work_entry_type_id.name or "").strip() if we.work_entry_type_id else ""
            is_home = self._entry_is_home_office(we, employee)
            is_base = self._entry_is_bonus_base_work(we)
            has_dates = bool(we.date_start and we.date_stop)

            _logger.info(
                "[BONUS CANDIDATE CHECK] we_id=%s code=%s name=%s start=%s stop=%s "
                "is_home=%s is_base=%s has_dates=%s duration=%s",
                we.id, code, name, we.date_start, we.date_stop,
                is_home, is_base, has_dates, we.duration
            )

            if is_home:
                continue
            if not has_dates:
                continue
            if not is_base:
                continue

            result |= we

        sorted_result = result.sorted(key=lambda r: r.date_start or fields.Datetime.now())

        _logger.info(
            "[BONUS CANDIDATES] employee=%s candidate_ids=%s",
            employee.name, sorted_result.ids
        )
        return sorted_result

    def _merge_bonus_work_entries(self, employee, date_from, date_to):
        """
        Une entradas contiguas o casi contiguas para formar bloques reales de turno.
        """
        tzname = self._company_tz(employee)
        # Traemos un dia adicional a cada lado para recomponer turnos
        # nocturnos que el calendario partio a medianoche.
        search_from = date_from - timedelta(days=1)
        search_to = date_to + timedelta(days=1)
        entries = self._get_bonus_candidate_entries(employee, search_from, search_to)

        if not entries:
            _logger.info("[BONUS MERGE] employee=%s no_entries", employee.name)
            return []

        merged = []
        gap_tolerance = timedelta(minutes=1)

        current_start = False
        current_stop = False
        current_ids = []

        for we in entries:
            start_local = _as_local(we.date_start, tzname)
            stop_local = _as_local(we.date_stop, tzname)

            _logger.info(
                "[BONUS MERGE ENTRY] we_id=%s start_local=%s stop_local=%s",
                we.id, start_local, stop_local
            )

            if not start_local or not stop_local or stop_local <= start_local:
                _logger.info(
                    "[BONUS MERGE SKIP] we_id=%s invalid_range start_local=%s stop_local=%s",
                    we.id, start_local, stop_local
                )
                continue

            if not current_start:
                current_start = start_local
                current_stop = stop_local
                current_ids = [we.id]
                continue

            if start_local <= (current_stop + gap_tolerance):
                if stop_local > current_stop:
                    current_stop = stop_local
                current_ids.append(we.id)
            else:
                merged.append({
                    "start_local": current_start,
                    "stop_local": current_stop,
                    "entry_ids": list(current_ids),
                })
                current_start = start_local
                current_stop = stop_local
                current_ids = [we.id]

        if current_start:
            merged.append({
                "start_local": current_start,
                "stop_local": current_stop,
                "entry_ids": list(current_ids),
            })

        for idx, block in enumerate(merged, 1):
            _logger.info(
                "[BONUS MERGED BLOCK] idx=%s start_local=%s stop_local=%s entry_ids=%s",
                idx, block["start_local"], block["stop_local"], block["entry_ids"]
            )

        return merged

    # ==========================
    # Festivos
    # ==========================
    def _is_calendar_holiday(self, local_dt, employee):
        company = self._company_get(employee)
        tzname = self._company_tz(employee)
        local_date = local_dt.date() if isinstance(local_dt, datetime) else local_dt

        calendar_id = employee.resource_calendar_id or company.resource_calendar_id

        if calendar_id:
            start_loc, end_loc = _local_day_bounds(local_date, tzname)
            start_utc, end_utc = _local_bounds_to_utc(start_loc, end_loc)

            leaves = self.env["resource.calendar.leaves"].search([
                ("calendar_id", "=", calendar_id.id),
                ("date_from", "<=", end_utc),
                ("date_to", ">=", start_utc),
                ("resource_id", "=", False),
            ], limit=1)
            if leaves:
                _logger.info(
                    "[BONUS HOLIDAY] date=%s employee=%s source=calendar_leaves leave_id=%s",
                    local_date, employee.name, leaves.id
                )
                return True

        if "hr.holidays.public.line" in self.env:
            hol = self.env["hr.holidays.public.line"].search([
                ("date", "=", local_date),
            ], limit=1)
            if hol:
                _logger.info(
                    "[BONUS HOLIDAY] date=%s employee=%s source=public_holiday holiday_id=%s",
                    local_date, employee.name, hol.id
                )
                return True

        holiday_codes = set(self._get_holiday_codes(company))
        if holiday_codes:
            start_loc, end_loc = _local_day_bounds(local_date, tzname)
            start_utc, end_utc = _local_bounds_to_utc(start_loc, end_loc)

            we_holiday = self.env["hr.work.entry"].search([
                ("employee_id", "=", employee.id),
                ("date_start", "<=", end_utc),
                ("date_stop", ">=", start_utc),
                ("work_entry_type_id.code", "in", list(holiday_codes)),
            ], limit=1)

            if we_holiday:
                _logger.info(
                    "[BONUS HOLIDAY] date=%s employee=%s source=work_entry we_id=%s we_code=%s",
                    local_date, employee.name, we_holiday.id, we_holiday.work_entry_type_id.code
                )
                return True

        _logger.info(
            "[BONUS HOLIDAY] date=%s employee=%s source=none",
            local_date, employee.name
        )
        return False

    # ==========================
    # Diferimiento por quincena
    # ==========================
    def _previous_quincena_range(self, dfrom, dto):
        if dfrom.day <= 15 and dto.day <= 15:
            prev_month = (dfrom.month - 1) or 12
            prev_year = dfrom.year - 1 if prev_month == 12 else dfrom.year
            last_prev = calendar.monthrange(prev_year, prev_month)[1]
            return (
                datetime(prev_year, prev_month, 16).date(),
                datetime(prev_year, prev_month, last_prev).date(),
            )
        return (
            datetime(dfrom.year, dfrom.month, 1).date(),
            datetime(dfrom.year, dfrom.month, 15).date(),
        )

    def _effective_range_for_payment(self, employee, date_from, date_to):
        company = self._company_get(employee)
        if self._defer_to_next_quincena(company):
            return self._previous_quincena_range(date_from, date_to)
        return (date_from, date_to)

    # ==========================
    # Reglas configurables
    # ==========================
    def _get_time_rules(self, employee, rule_type):
        company = self._company_get(employee)
        rules = self.env["hr.rule.time.window"].sudo().search([
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("rule_type", "=", rule_type),
        ], order="sequence, id")

        for rule in rules:
            _logger.info(
                "[BONUS RULE] id=%s type=%s seq=%s normal=%s sunday=%s holiday=%s "
                "check_in=%s->%s check_out=%s->%s date_from=%s date_to=%s",
                rule.id,
                rule.rule_type,
                getattr(rule, "sequence", False),
                rule.apply_on_normal,
                rule.apply_on_sunday,
                rule.apply_on_holiday,
                rule.check_in_from,
                rule.check_in_to,
                rule.check_out_from,
                rule.check_out_to,
                rule.date_from,
                rule.date_to,
            )

        return rules

    def _time_rule_applies_to_day(self, rule, cur_day, is_sunday, is_holiday):
        if rule.date_from and cur_day < rule.date_from:
            return False

        if rule.date_to and cur_day > rule.date_to:
            return False

        if is_sunday or is_holiday:
            applies = False
            if is_sunday and rule.apply_on_sunday:
                applies = True
            if is_holiday and rule.apply_on_holiday:
                applies = True
            return applies

        return bool(rule.apply_on_normal)

    def _get_block_day_contexts(self, block, employee):
        """
        Devuelve los días candidatos que toca un bloque y la marca de si el
        datetime de inicio/fin cae dentro de cada día.

        Esto permite evaluar bien turnos cruzados.
        """
        start_local = block["start_local"]
        stop_local = block["stop_local"]

        start_date = start_local.date()
        stop_date = stop_local.date()

        dates = [start_date]
        if stop_date != start_date:
            dates.append(stop_date)

        result = []
        for d in dates:
            day_start, day_end = _local_day_bounds(d, self._company_tz(employee))
            touches_start = (start_local.date() == d)
            touches_stop = (stop_local.date() == d)

            result.append({
                "date": d,
                "touches_start": touches_start,
                "touches_stop": touches_stop,
                "day_start": day_start,
                "day_end": day_end,
            })

        return result

    def _evaluate_block_against_rule_for_day(self, block, day_ctx, rule, is_special):
        """
        Evalúa el bloque contra una regla para un día específico.

        Lógica:
        - en normal: exigir entrada del día
        - en domingo/festivo: permitir entrada o salida del día
        - adicionalmente, para domingo/festivo, permitir entrada exacta al límite final
          cuando el negocio espera reconocer jornadas tipo 00:00-06:00 o 06:00-14:00
          del mismo día especial
        """
        start_local = block["start_local"]
        stop_local = block["stop_local"]

        in_start = self._float_to_time(rule.check_in_from)
        in_end = self._float_to_time(rule.check_in_to)
        out_start = self._float_to_time(rule.check_out_from)
        out_end = self._float_to_time(rule.check_out_to)

        qualifies_in = False
        qualifies_out = False

        # Evaluar solo si el start realmente cae en ese día
        if day_ctx["touches_start"]:
            qualifies_in = _time_in_window(
                start_local, in_start, in_end,
                inclusive_end=is_special
            )

        # Evaluar solo si el stop realmente cae en ese día
        if day_ctx["touches_stop"]:
            qualifies_out = _time_in_window(
                stop_local, out_start, out_end,
                inclusive_end=False
            )

        _logger.info(
            "[BONUS DAY RULE EVAL] date=%s is_special=%s touches_start=%s touches_stop=%s "
            "start_local=%s stop_local=%s "
            "in_window=%s->%s qualifies_in=%s "
            "out_window=%s->%s qualifies_out=%s",
            day_ctx["date"],
            is_special,
            day_ctx["touches_start"],
            day_ctx["touches_stop"],
            start_local,
            stop_local,
            in_start, in_end, qualifies_in,
            out_start, out_end, qualifies_out,
        )

        if is_special:
            return qualifies_in or qualifies_out

        return qualifies_in or qualifies_out

    # ==========================
    # Conteos por día (movilidad / rodamiento)
    # ==========================
    def _count_days_for_configurable_rule(self, employee, date_from, date_to, rule_type):
        """
        Lógica final para convivir con ambos casos:

        1. Se toman solo asistencias base.
        2. Se unen bloques contiguos.
        3. Cada bloque puede aportar al día de inicio y/o al día de fin.
        4. Cada día se evalúa por separado.
        5. En día normal: cuenta por entrada del día.
        6. En domingo/festivo: cuenta por entrada o salida del día.
        7. Un mismo día solo cuenta una vez.
        """
        rules = self._get_time_rules(employee, rule_type=rule_type)
        if not rules:
            _logger.info(
                "[BONUS DAYS] employee=%s rule_type=%s no_rules",
                employee.name, rule_type
            )
            return 0

        merged_blocks = self._merge_bonus_work_entries(employee, date_from, date_to)
        if not merged_blocks:
            _logger.info(
                "[BONUS DAYS] employee=%s rule_type=%s no_merged_blocks",
                employee.name, rule_type
            )
            return 0

        holiday_cache = {}
        counted_dates = set()

        def is_public_holiday(d):
            if d not in holiday_cache:
                holiday_cache[d] = self._is_calendar_holiday(d, employee)
            return holiday_cache[d]

        _logger.info(
            "[BONUS DAYS START] employee=%s rule_type=%s range=%s..%s",
            employee.name, rule_type, date_from, date_to
        )

        for idx, block in enumerate(merged_blocks, 1):
            start_local = block["start_local"]
            stop_local = block["stop_local"]

            if not start_local or not stop_local or stop_local <= start_local:
                _logger.info(
                    "[BONUS BLOCK SKIP] idx=%s reason=invalid_range start=%s stop=%s",
                    idx, start_local, stop_local
                )
                continue

            _logger.info(
                "[BONUS BLOCK START] idx=%s start=%s stop=%s entry_ids=%s",
                idx, start_local, stop_local, block["entry_ids"]
            )

            day_contexts = self._get_block_day_contexts(block, employee)

            for day_ctx in day_contexts:
                cur_day = day_ctx["date"]

                if not (date_from <= cur_day <= date_to):
                    _logger.info(
                        "[BONUS DAY SKIP] idx=%s date=%s reason=out_of_range",
                        idx, cur_day
                    )
                    continue

                if (employee.id, cur_day, rule_type) in counted_dates:
                    _logger.info(
                        "[BONUS DAY SKIP] idx=%s date=%s reason=already_counted",
                        idx, cur_day
                    )
                    continue

                is_sun = cur_day.weekday() == 6
                is_hol = is_public_holiday(cur_day)
                is_special = bool(is_sun or is_hol)

                _logger.info(
                    "[BONUS DAY CONTEXT] idx=%s date=%s is_sunday=%s is_holiday=%s "
                    "is_special=%s touches_start=%s touches_stop=%s",
                    idx, cur_day, is_sun, is_hol, is_special,
                    day_ctx["touches_start"], day_ctx["touches_stop"]
                )

                day_counted = False

                for rule in rules:
                    applies = self._time_rule_applies_to_day(rule, cur_day, is_sun, is_hol)

                    _logger.info(
                        "[BONUS RULE APPLY CHECK] idx=%s date=%s rule_id=%s applies=%s",
                        idx, cur_day, rule.id, applies
                    )

                    if not applies:
                        continue

                    eval_day_ctx = dict(day_ctx)
                    # Si el bloque quedo cortado exactamente al cierre del periodo,
                    # no debemos tomar ese stop como una salida real del turno.
                    if (
                        eval_day_ctx["touches_stop"]
                        and cur_day == date_to
                        and stop_local >= (eval_day_ctx["day_end"] - timedelta(seconds=1))
                    ):
                        eval_day_ctx["touches_stop"] = False

                    qualifies = self._evaluate_block_against_rule_for_day(
                        block=block,
                        day_ctx=eval_day_ctx,
                        rule=rule,
                        is_special=is_special,
                    )

                    if qualifies:
                        counted_dates.add((employee.id, cur_day, rule_type))
                        day_counted = True
                        _logger.info(
                            "[BONUS COUNTED] idx=%s date=%s rule_id=%s reason=%s",
                            idx,
                            cur_day,
                            rule.id,
                            "special_day" if is_special else "normal_day",
                        )
                        break

                if not day_counted:
                    _logger.info(
                        "[BONUS DAY RESULT] idx=%s date=%s result=not_counted",
                        idx, cur_day
                    )

        _logger.info(
            "[BONUS DAYS RESULT] employee=%s rule_type=%s range=%s..%s counted_dates=%s total=%s",
            employee.name,
            rule_type,
            date_from,
            date_to,
            sorted(list(counted_dates), key=lambda x: x[1]),
            len(counted_dates),
        )

        return len(counted_dates)

    # ==========================
    # Recargos: sumar WE ya generados
    # ==========================
    def _sum_work_entry_hours_by_codes(self, employee, date_from, date_to, codes):
        entries = self._search_work_entries_localized(employee, date_from, date_to)
        total = 0.0
        code_set = {c.strip().upper() for c in codes if c}

        for we in entries:
            if self._entry_is_home_office(we, employee):
                continue
            code = (we.work_entry_type_id.code or "").strip().upper() if we.work_entry_type_id else ""
            if code in code_set:
                total += we.duration or 0.0

        return round(total, 2)

    # ==========================
    # API para reglas salariales
    # ==========================
    def _compute_bono_movilidad_days(self, contract, date_from, date_to):
        employee = contract.employee_id
        dfrom_eff, dto_eff = self._effective_range_for_payment(employee, date_from, date_to)
        return self._count_days_for_configurable_rule(employee, dfrom_eff, dto_eff, "mobility")

    def _compute_aux_rodamiento_days(self, contract, date_from, date_to):
        employee = contract.employee_id
        dfrom_eff, dto_eff = self._effective_range_for_payment(employee, date_from, date_to)
        return self._count_days_for_configurable_rule(employee, dfrom_eff, dto_eff, "rodamiento")

    def _compute_hours_recargo_nocturno(self, contract, date_from, date_to):
        employee = contract.employee_id
        dfrom_eff, dto_eff = self._effective_range_for_payment(employee, date_from, date_to)
        return self._sum_work_entry_hours_by_codes(employee, dfrom_eff, dto_eff, ["HRN"])

    def _compute_hours_recargo_nocturno_fest(self, contract, date_from, date_to):
        employee = contract.employee_id
        dfrom_eff, dto_eff = self._effective_range_for_payment(employee, date_from, date_to)
        return self._sum_work_entry_hours_by_codes(employee, dfrom_eff, dto_eff, ["HRNDF"])

    def _compute_hours_recargo_diurno_dom(self, contract, date_from, date_to):
        employee = contract.employee_id
        dfrom_eff, dto_eff = self._effective_range_for_payment(employee, date_from, date_to)
        return self._sum_work_entry_hours_by_codes(employee, dfrom_eff, dto_eff, ["HRDDF"])
