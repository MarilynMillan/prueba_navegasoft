# -*- coding: utf-8 -*-
import calendar
import logging
import pytz

from datetime import datetime, timedelta, time, date

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class PlanningSlotPayrollExt(models.Model):
    _inherit = "planning.slot"

    # =========================================================
    # Campos Matriz
    # =========================================================
    matrix_day = fields.Date(index=True)

    matrix_code = fields.Char(string="Código matriz", index=True)
    is_rest_day = fields.Boolean(string="Día de descanso", default=False)

    # =========================================================
    # Flujo de aprobacion
    # =========================================================
    approval_state = fields.Selection([
        ("draft",           "Borrador"),
        ("submitted",       "Enviado"),
        ("waiting_manager", "En revisión (L1)"),
        ("waiting_hr",      "En revisión (L2)"),
        ("approved",        "Aprobado"),
        ("rejected",        "Rechazado"),
        ("cancelled",       "Cancelado"),
    ], default="draft", string="Estado de Aprobación")

    approver_level1_id = fields.Many2one("res.users", string="Aprobador L1", readonly=True)
    approver_level2_id = fields.Many2one("res.users", string="Aprobador L2", readonly=True)
    approval_comment   = fields.Text("Comentario de Aprobación/Rechazo")

    resources_ids = fields.Many2many("resource.resource", string="Recursos Asignados")

    # =========================================================
    # Flags de idempotencia
    # =========================================================
    work_entries_generated = fields.Boolean(string="WE base generados",     default=False, copy=False, index=True)
    recargos_generated     = fields.Boolean(string="WE recargos generados", default=False, copy=False, index=True)

    # ------------------------------------------------------------
    # Helpers TZ
    # ------------------------------------------------------------
    def _get_company_tz(self):
        tz_name = self.company_id.resource_calendar_id.tz or self.company_id.partner_id.tz or "UTC"
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _localize_safe(self, tz, dt_naive):
        try:
            return tz.localize(dt_naive, is_dst=None)
        except Exception:
            return tz.localize(dt_naive, is_dst=False)

    def _day_to_utc_range(self, day_date, start_t=None, end_t=None):
        tz = self._get_company_tz()

        if not start_t and not end_t:
            start_local = self._localize_safe(tz, datetime.combine(day_date, time.min))
            end_local   = self._localize_safe(tz, datetime.combine(day_date + timedelta(days=1), time.min))
            return (
                start_local.astimezone(pytz.UTC).replace(tzinfo=None),
                end_local.astimezone(pytz.UTC).replace(tzinfo=None),
            )

        start_t = start_t or time.min
        start_dt_local = self._localize_safe(tz, datetime.combine(day_date, start_t))

        if end_t is None:
            end_dt_local = self._localize_safe(tz, datetime.combine(day_date + timedelta(days=1), time.min))
        else:
            end_dt_local = self._localize_safe(tz, datetime.combine(day_date, end_t))
            if end_dt_local <= start_dt_local:
                end_dt_local = self._localize_safe(tz, datetime.combine(day_date + timedelta(days=1), end_t))

        end_dt_utc = end_dt_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_dt_utc = self._normalize_end_datetime_utc(end_dt_utc)

        return (
            start_dt_local.astimezone(pytz.UTC).replace(tzinfo=None),
            end_dt_utc,
        )

    def _normalize_end_datetime_utc(self, end_utc_naive):
        """23:59:00 local -> 23:59:59 local (devuelve UTC naive)."""
        if not end_utc_naive:
            return end_utc_naive
        tz = self._get_company_tz()
        if isinstance(end_utc_naive, datetime) and end_utc_naive.tzinfo is None:
            end_aware = pytz.UTC.localize(end_utc_naive)
        else:
            end_aware = end_utc_naive
        end_local = end_aware.astimezone(tz)
        if end_local.hour == 23 and end_local.minute == 59 and end_local.second == 0:
            end_local = end_local.replace(second=59, microsecond=0)
            return end_local.astimezone(pytz.UTC).replace(tzinfo=None)
        return end_aware.astimezone(pytz.UTC).replace(tzinfo=None)

    # ------------------------------------------------------------
    # Helper: tipo de WE de Asistencia (robusto, sin asumir campos)
    # ------------------------------------------------------------
    def _get_attendance_work_entry_type(self):
        """
        Busca el hr.work.entry.type de Asistencia con múltiples estrategias,
        sin asumir campos específicos del contrato (compatibilidad Odoo 16/17/18).

        Orden de búsqueda:
          1. work_entry_type_id del propio planning.slot (Odoo 18 lo tiene).
          2. work_entry_type_id del contrato vigente (getattr seguro).
          3. WEs nativas recientes del empleado (sin leave_id ni planning_slot_id).
          4. Código WORK100 (estándar Odoo).
          5. Nombre contiene "Asistencia" o "Attendance".
          6. Primer tipo cuyo code empieza por "WORK".
          7. None → fallback en _ensure_work_entries_once().
        """
        self.ensure_one()
        WET = self.env["hr.work.entry.type"].sudo()

        # 1. Campo propio del slot (Odoo 18 planning tiene work_entry_type_id)
        wet = getattr(self, "work_entry_type_id", None)
        if wet and wet.id:
            _logger.debug("[WET] Slot %s: tipo desde slot.work_entry_type_id = %s", self.id, wet.code)
            return wet

        # 2. Contrato vigente del empleado
        employee_sudo = self.employee_id.sudo()
        contract = getattr(employee_sudo, "contract_id", None)
        if not contract:
            contract_ids = getattr(employee_sudo, "contract_ids", None)
            if contract_ids:
                contract = contract_ids.filtered(
                    lambda c: getattr(c, "state", "") == "open"
                )[:1]
        if contract:
            wet = getattr(contract, "work_entry_type_id", None)
            if wet and wet.id:
                _logger.debug("[WET] Slot %s: tipo desde contrato = %s", self.id, wet.code)
                return wet

        # 3. WEs nativas del empleado (sin leave_id, sin planning_slot_id)
        #    Son las que Odoo crea para dias normales de trabajo.
        ref_we = self.env["hr.work.entry"].sudo().search([
            ("employee_id",      "=", self.employee_id.id),
            ("leave_id",         "=", False),
            ("planning_slot_id", "=", False),
        ], limit=1, order="date_start desc")
        if ref_we and ref_we.work_entry_type_id:
            wet = ref_we.work_entry_type_id
            _logger.debug("[WET] Slot %s: tipo desde WE nativa existente = %s", self.id, wet.code)
            return wet

        # 4. Código estándar WORK100
        wet = WET.search([("code", "=", "WORK100")], limit=1)
        if wet:
            _logger.debug("[WET] Slot %s: tipo por código WORK100", self.id)
            return wet

        # 5. Nombre contiene Asistencia / Attendance
        wet = WET.search([
            "|",
            ("name", "ilike", "Asistencia"),
            ("name", "ilike", "Attendance"),
        ], limit=1)
        if wet:
            _logger.debug("[WET] Slot %s: tipo por nombre Asistencia/Attendance = %s", self.id, wet.name)
            return wet

        # 6. Code empieza por WORK
        wet = WET.search([("code", "=like", "WORK%")], limit=1)
        if wet:
            _logger.debug("[WET] Slot %s: tipo por código WORK* = %s", self.id, wet.code)
            return wet

        _logger.warning("[WET] Slot %s (emp=%s): NO se encontró work_entry_type de Asistencia.",
                        self.id, self.employee_id.name)
        return None

    # ------------------------------------------------------------
    # Helpers horas desde plantilla
    # ------------------------------------------------------------
    def _tpl_hours(self, tmpl):
        if not tmpl:
            return (None, None)
        hour_from = getattr(tmpl, "hour_from", None)
        hour_to   = getattr(tmpl, "hour_to",   None)
        if hour_from is None:
            hour_from = getattr(tmpl, "start_time", None)
        if hour_to is None:
            hour_to = getattr(tmpl, "end_time", None)

        def float_to_time(h):
            hh = int(h)
            mm = int(round((h - hh) * 60))
            if mm >= 60:
                hh += 1
                mm = 0
            return time(hh % 24, mm)

        if isinstance(hour_from, (int, float)) and isinstance(hour_to, (int, float)):
            return (float_to_time(hour_from), float_to_time(hour_to))
        return (None, None)

    # ------------------------------------------------------------
    # Helpers template
    # ------------------------------------------------------------
    def _get_template_from_vals(self, vals):
        tmpl = None
        if "slot_template_id" in self._fields:
            tmpl_id = vals.get("slot_template_id") or (self.slot_template_id.id if self.slot_template_id else False)
            tmpl = self.env["planning.slot.template"].sudo().browse(tmpl_id) if tmpl_id else None
        elif "template_id" in self._fields:
            tmpl_id = vals.get("template_id") or (self.template_id.id if self.template_id else False)
            tmpl = self.env["planning.slot.template"].sudo().browse(tmpl_id) if tmpl_id else None
        return tmpl if tmpl and tmpl.exists() else None

    def _set_template_in_vals(self, vals, tmpl):
        vals = dict(vals)
        if not tmpl:
            return vals
        if "slot_template_id" in self._fields:
            vals["slot_template_id"] = tmpl.id
        if "template_id" in self._fields:
            vals["template_id"] = tmpl.id
        return vals

    def _resolve_template_by_code(self, code):
        if not code:
            return None
        return self.env["planning.slot.template"].sudo().search([("code", "=", code)], limit=1)

    def _template_is_rest(self, tmpl):
        if not tmpl:
            return False
        if "is_rest_template" in tmpl._fields and tmpl.is_rest_template:
            return True
        if getattr(tmpl, "code", False) == "D":
            return True
        return False

    def _apply_matrix_template_and_ranges(self, vals):
        vals = dict(vals)
        code = vals.get("matrix_code") or vals.get("code") or self.matrix_code
        tmpl = self._get_template_from_vals(vals)
        if not tmpl and code:
            tmpl = self._resolve_template_by_code(code)
            if tmpl:
                vals = self._set_template_in_vals(vals, tmpl)
        tmpl = self._get_template_from_vals(vals)
        is_rest = bool(vals.get("is_rest_day", self.is_rest_day))
        if tmpl and self._template_is_rest(tmpl):
            is_rest = True
            vals["is_rest_day"] = True
        if is_rest:
            day_val = vals.get("matrix_day") or self.matrix_day
            if day_val:
                d = fields.Date.to_date(day_val)
                t_from, t_to = self._tpl_hours(tmpl) if tmpl else (None, None)
                if t_from and t_to:
                    s_utc, e_utc = self._day_to_utc_range(d, start_t=t_from, end_t=t_to)
                else:
                    s_utc, e_utc = self._day_to_utc_range(d)
                vals["start_datetime"] = s_utc
                vals["end_datetime"]   = e_utc
        if code:
            vals["matrix_code"] = code
        if "end_datetime" in vals and vals["end_datetime"]:
            end_dt = fields.Datetime.to_datetime(vals["end_datetime"])
            if end_dt:
                vals["end_datetime"] = self._normalize_end_datetime_utc(end_dt)
        return vals

    # ------------------------------------------------------------
    # Seguridad
    # ------------------------------------------------------------
    def _is_planning_manager_user(self, user=None):
        user = user or self.env.user
        return bool(
            self.env.is_superuser()
            or user.has_group("base.group_system")
            or user.has_group("planning.group_planning_manager")
        )

    def _is_hr_approver_user(self, user=None):
        user = user or self.env.user
        return bool(
            self.env.is_superuser()
            or user.has_group("base.group_system")
            or user.has_group("hr_holidays.group_hr_holidays_manager")
        )

    def _is_manager(self):
        return self._is_planning_manager_user() or self._is_hr_approver_user()

    def _is_admin(self):
        return self._is_hr_approver_user()

    def _dept_domain_for_user(self, user):
        emp = user.employee_id
        if not emp or not emp.department_id:
            return [("id", "=", -1)]
        return ["|", ("id", "=", emp.department_id.id), ("id", "child_of", emp.department_id.id)]

    def _check_planning_write_rights(self):
        self.ensure_one()
        user = self.env.user
        if self._is_manager():
            return
        if self.employee_id and self.employee_id.user_id == user:
            return
        emp = user.employee_id
        if emp and self.employee_id and self.employee_id.department_id:
            depts = self.env["hr.department"].search(self._dept_domain_for_user(user))
            if self.employee_id.department_id.id in depts.ids:
                return
        raise AccessError(_("No tiene permisos para modificar este turno."))

    def _validate_datetimes(self, values=None):
        def getv(name, default):
            if values and name in values:
                return values[name]
            return getattr(self, name, default)
        start = getv("start_datetime", None)
        end   = getv("end_datetime",   None)
        if start and end:
            s = fields.Datetime.to_datetime(start)
            e = fields.Datetime.to_datetime(end)
            if not s or not e or e <= s:
                raise UserError(_("La fecha fin debe ser mayor a la fecha inicio."))

    # =========================================================
    # Work entries — limpieza e idempotencia
    # =========================================================
    def _cleanup_work_entries_for_slot(self, only_types=None, only_draft=True, force_admin=False):
        self.ensure_one()
        WE = self.env["hr.work.entry"].sudo()
        dom = [("planning_slot_id", "=", self.id)]
        if only_types:
            dom.append(("work_entry_type_id", "in", list(only_types)))
        entries = WE.search(dom)
        if not entries:
            return
        if only_draft:
            entries.filtered(lambda w: w.state == "draft")._soft_remove_entries()
            return
        if not (self._is_manager() or self._is_admin() or force_admin):
            entries.filtered(lambda w: w.state == "draft")._soft_remove_entries()
            return
        validated = entries.filtered(lambda w: w.state == "validated")
        if validated:
            validated.write({"state": "draft"})
        entries._soft_remove_entries()

    def _drop_template_on_manual_datetime_override(self, vals):
        """
        Si el usuario ajusta manualmente start/end sin cambiar la plantilla,
        soltamos el vínculo con template para que el core no vuelva a imponer
        sus horas al recomputar.
        """
        vals = dict(vals or {})
        manual_dt_change = all(k in vals for k in ("start_datetime", "end_datetime"))
        manual_template_change = any(k in vals for k in ("template_id", "slot_template_id", "matrix_code"))
        if not manual_dt_change or manual_template_change:
            return vals

        has_template = bool(
            ("template_id" in self._fields and self.template_id)
            or ("slot_template_id" in self._fields and self.slot_template_id)
        )
        if not has_template:
            return vals

        if "template_id" in self._fields and "template_id" not in vals:
            vals["template_id"] = False
        if "slot_template_id" in self._fields and "slot_template_id" not in vals:
            vals["slot_template_id"] = False
        if "previous_template_id" in self._fields and "previous_template_id" not in vals:
            vals["previous_template_id"] = False
        if "template_reset" in self._fields and "template_reset" not in vals:
            vals["template_reset"] = True
        return vals

    def _ensure_work_entries_once(self):
        """
        Genera la WE de Asistencia para el slot cubriendo el rango COMPLETO
        del turno (start_datetime → end_datetime), sin importar el horario
        del contrato o festivos.

        FIX CRÍTICO — planning_slot_id en la WE de Asistencia:
        --------------------------------------------------------
        El flujo nativo action_send() crea WEs basadas en la INTERSECCIÓN
        del turno con el horario del contrato. En días festivos esto produce
        WEs parciales (ej: solo 06:00-08:00 de un turno 06:00-14:00) porque
        el resto del horario queda cubierto por la ausencia de festivo.

        En cambio, para nómina con planning, la regla de negocio es que la
        WE de Asistencia debe cubrir TODO el rango del turno aprobado.

        Además, las WEs creadas sin planning_slot_id son eliminadas por
        _cleanup_leave_entries_conflicting_with_slots(). Por eso creamos
        la WE manualmente con planning_slot_id desde el inicio.

        El tipo se resuelve con _get_attendance_work_entry_type() que tiene
        7 estrategias de fallback sin asumir campos del contrato.
        """
        for rec in self:
            if rec.work_entries_generated:
                continue

            # Verificar si ya existe WE de asistencia para este slot
            # (excluimos recargos buscando por tipo si hay forma de distinguir)
            existing = self.env["hr.work.entry"].sudo().search([
                ("planning_slot_id", "=", rec.id),
            ])
            # Si solo hay recargos (tipos de la lista de recargo), seguimos
            recargo_type_ids = set(
                rec._get_recargo_rules().mapped("work_entry_type_id").ids
            )
            has_attendance_we = existing.filtered(
                lambda w: w.work_entry_type_id.id not in recargo_type_ids
            )
            if has_attendance_we:
                rec._normalize_existing_attendance_work_entries(has_attendance_we)
                rec._cleanup_non_slot_work_entries_for_day()
                rec.sudo().write({"work_entries_generated": True})
                continue

            # Normalizar end_datetime 23:59:00 → 23:59:59
            end_raw = fields.Datetime.to_datetime(rec.end_datetime)
            if end_raw:
                end_fixed = rec._normalize_end_datetime_utc(end_raw)
                if end_fixed and end_fixed != end_raw:
                    rec.sudo().write({"end_datetime": end_fixed})

            start_dt = fields.Datetime.to_datetime(rec.start_datetime)
            end_dt   = fields.Datetime.to_datetime(rec.end_datetime)

            if not start_dt or not end_dt or start_dt >= end_dt:
                _logger.warning(
                    "[WE ASISTENCIA] Slot id=%s emp=%s — fechas inválidas, omitiendo.",
                    rec.id, rec.employee_id.name,
                )
                rec.sudo().write({"work_entries_generated": True})
                continue

            # Obtener tipo de WE de Asistencia
            work_entry_type = rec._get_attendance_work_entry_type()
            effective_contract = rec._get_effective_contract_for_slot()

            if work_entry_type:
                tz = rec._get_company_tz()
                work_day = pytz.UTC.localize(start_dt).astimezone(tz).date()
                pay_from, pay_to, pay_date, pay_label = rec._compute_pay_period_mes_caido(work_day)
                duration_hours = (end_dt - start_dt).total_seconds() / 3600.0

                self.env["hr.work.entry"].sudo().create({
                    "name":                "Asistencia: %s" % rec.employee_id.name,
                    "employee_id":         rec.employee_id.id,
                    "work_entry_type_id":  work_entry_type.id,
                    "contract_id":         effective_contract.id if effective_contract else False,
                    "date_start":          start_dt,
                    "date_stop":           end_dt,
                    "planning_slot_id":    rec.id,       # ← excluye del cleanup
                    "state":               "draft",
                    "company_id":          rec.company_id.id,
                    "duration":            duration_hours,
                    "pay_period_start":    pay_from,
                    "pay_period_end":      pay_to,
                    "pay_period_pay_date": pay_date,
                    "pay_period_label":    pay_label,
                })

                _logger.info(
                    "[WE ASISTENCIA] Creada — tipo=%s emp=%s slot=%s "
                    "rango_utc=%s→%s (%.2fh) quincena=%s",
                    work_entry_type.code or work_entry_type.name,
                    rec.employee_id.name, rec.id,
                    start_dt, end_dt, duration_hours, pay_label,
                )
            else:
                _logger.warning(
                    "[WE ASISTENCIA] Slot %s (emp=%s): sin tipo. Usando action_send() nativo.",
                    rec.id, rec.employee_id.name,
                )
                super(PlanningSlotPayrollExt, rec).action_send()

            rec._cleanup_non_slot_work_entries_for_day()
            rec.sudo().write({"work_entries_generated": True})

    def _normalize_existing_attendance_work_entries(self, attendance_entries):
        for rec in self:
            entries = attendance_entries.filtered(lambda w: w.planning_slot_id == rec)
            if not entries:
                continue

            start_dt = fields.Datetime.to_datetime(rec.start_datetime)
            end_dt = fields.Datetime.to_datetime(rec.end_datetime)
            if not start_dt or not end_dt or start_dt >= end_dt:
                continue

            duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
            survivor = entries.sorted(lambda w: (w.date_start or datetime.min, w.id))[0]
            vals = {}
            if survivor.date_start != start_dt:
                vals["date_start"] = start_dt
            if survivor.date_stop != end_dt:
                vals["date_stop"] = end_dt
            if "duration" in survivor._fields and survivor.duration != duration_hours:
                vals["duration"] = duration_hours
            if survivor.state == "conflict":
                vals["state"] = "draft"

            if vals:
                _logger.info(
                    "[WE ASISTENCIA] Normalizando WE existente slot=%s we=%s vals=%s",
                    rec.id,
                    survivor.id,
                    vals,
                )
                survivor.with_context(
                    skip_full_day_leave_normalization=True,
                    skip_worked_time_leave_normalization=True,
                ).sudo().write(vals)

            duplicates = entries - survivor
            if duplicates:
                _logger.info(
                    "[WE ASISTENCIA] Desactivando duplicadas slot=%s we_ids=%s",
                    rec.id,
                    duplicates.ids,
                )
                duplicates._soft_remove_entries()

    def _cleanup_non_slot_work_entries_for_day(self):
        WorkEntry = self.env["hr.work.entry"].sudo()
        for rec in self.filtered(lambda s: s.employee_id and s.start_datetime and not s.is_rest_day):
            start_dt = fields.Datetime.to_datetime(rec.start_datetime)
            if not start_dt:
                continue

            tz = rec._get_company_tz()
            local_day = pytz.UTC.localize(start_dt).astimezone(tz).date()
            day_start_utc, day_end_utc = rec._day_to_utc_range(local_day)

            candidates = WorkEntry.search([
                ("employee_id", "=", rec.employee_id.id),
                ("planning_slot_id", "=", False),
                ("active", "=", True),
                ("state", "in", ["draft", "conflict", "validated"]),
                ("date_start", "<", day_end_utc),
                ("date_stop", ">", day_start_utc),
            ])
            if not candidates:
                continue

            _logger.info(
                "[WE ASISTENCIA] Cleanup non-slot WEs emp=%s slot=%s local_day=%s candidates=%s",
                rec.employee_id.name,
                rec.id,
                local_day,
                candidates.ids,
            )
            candidates._cleanup_leave_entries_conflicting_with_slots()

    def _generate_recargo_work_entries_once(self):
        for rec in self:
            if rec.is_rest_day:
                rec.sudo().write({"recargos_generated": True})
                continue
            if rec.recargos_generated:
                rec._sync_recargo_work_entries()
                continue
            rec._generate_recargo_work_entries()
            rec._sync_recargo_work_entries()
            rec.sudo().write({"recargos_generated": True})

    # =========================================================
    # Flujo aprobación
    # =========================================================
    def action_submit(self):
        for rec in self:
            rec._check_planning_write_rights()
            if rec.approval_state not in ("draft", "rejected"):
                raise UserError(_("Solo se puede enviar desde Borrador o Rechazado."))
            rec.approval_state = "submitted"
        return True

    def action_to_manager(self):
        for rec in self:
            rec._check_planning_write_rights()
            if rec.approval_state != "submitted":
                raise UserError(_("Debe estar Enviado."))
            rec.approval_state = "waiting_manager"
        return True

    def action_approve_l1(self):
        if not (self._is_manager() or self._is_admin()):
            raise AccessError(_("No es aprobador de Nivel 1."))
        user = self.env.user
        for rec in self:
            if rec.approval_state != "waiting_manager":
                raise UserError(_("Debe estar En revision (L1)."))
            rec.write({"approval_state": "waiting_hr", "approver_level1_id": user.id})
        return True

    def action_approve_l2(self):
        if not self._is_admin():
            raise AccessError(_("No es aprobador de Nivel 2."))
        user = self.env.user
        for rec in self:
            if rec.approval_state != "waiting_hr":
                raise UserError(_("Debe estar En revision (L2)."))
            rec.write({"approval_state": "approved", "approver_level2_id": user.id})
            rec._ensure_work_entries_once()
            rec._generate_recargo_work_entries_once()
        return True

    def action_auto_approve_from_matrix(self):
        if not self._is_manager():
            raise AccessError(_("No tiene permisos para autoaprobar turnos."))
        user = self.env.user
        for rec in self:
            if rec.approval_state in ("approved", "cancelled"):
                continue
            vals = {"approval_state": "approved", "approver_level2_id": user.id}
            if not rec.approver_level1_id:
                vals["approver_level1_id"] = user.id
            rec.write(vals)
            rec._ensure_work_entries_once()
            rec._generate_recargo_work_entries_once()
        return True

    def action_send(self):
        return super().action_send()

    def action_reject(self, reason=None):
        if not self._is_manager():
            raise AccessError(_("No tiene permisos para rechazar turnos."))
        for rec in self:
            if rec.approval_state in ("approved", "cancelled"):
                raise UserError(_("No se puede rechazar un turno aprobado/cancelado."))
            rec.write({"approval_state": "rejected", "approval_comment": reason or rec.approval_comment})
        return True

    def action_reset_to_draft(self):
        for rec in self:
            rec._check_planning_write_rights()
            if rec.approval_state not in ("rejected", "cancelled"):
                raise UserError(_("Solo puede reiniciar a Borrador desde Rechazado o Cancelado."))
            rec._cleanup_work_entries_for_slot(only_types=None, only_draft=True)
            rec.write({
                "approval_state":         "draft",
                "approver_level1_id":     False,
                "approver_level2_id":     False,
                "approval_comment":       False,
                "work_entries_generated": False,
                "recargos_generated":     False,
            })
        return True

    def action_cancel(self, reason=None):
        for rec in self:
            rec._check_planning_write_rights()
            rec.write({"approval_state": "cancelled", "approval_comment": reason or rec.approval_comment})
            rec._cleanup_work_entries_for_slot(only_types=None, only_draft=True)
        return True

    # =========================================================
    # CRUD
    # =========================================================
    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        normalized = []
        for vals in vals_list:
            vals = dict(vals or {})
            tmp = self.new(vals)
            vals = tmp._apply_matrix_template_and_ranges(vals)
            if "end_datetime" in vals and vals["end_datetime"]:
                end_dt = fields.Datetime.to_datetime(vals["end_datetime"])
                if end_dt:
                    fixed = tmp._normalize_end_datetime_utc(end_dt)
                    if fixed:
                        vals["end_datetime"] = fixed
            tmp2 = self.new(vals)
            tmp2._validate_datetimes(vals)
            normalized.append(vals)
        recs = super().create(normalized)
        for rec in recs:
            rec._check_planning_write_rights()
        recs.sudo().write({"work_entries_generated": False, "recargos_generated": False})
        return recs

    def write(self, vals):
        for r in self:
            vals2 = r._apply_matrix_template_and_ranges(vals)
            vals2 = r._drop_template_on_manual_datetime_override(vals2)
            if "end_datetime" in vals2 and vals2["end_datetime"]:
                end_dt = fields.Datetime.to_datetime(vals2["end_datetime"])
                if end_dt:
                    fixed = r._normalize_end_datetime_utc(end_dt)
                    if fixed:
                        vals2["end_datetime"] = fixed
            r._validate_datetimes(vals2)
            r._check_planning_write_rights()
            relevant = {"start_datetime", "end_datetime", "template_id", "slot_template_id", "is_rest_day"}
            if any(k in vals2 for k in relevant):
                vals2.update({"work_entries_generated": False, "recargos_generated": False})
                r._cleanup_work_entries_for_slot(only_types=None, only_draft=True)
            super(PlanningSlotPayrollExt, r).write(vals2)
        return True

    def unlink(self):
        for r in self:
            r._check_planning_write_rights()
            if r.approval_state not in ("draft", "rejected", "cancelled"):
                raise UserError(_("Solo puede eliminar turnos en Borrador, Rechazado o Cancelado."))
            r._cleanup_work_entries_for_slot(only_types=None, only_draft=True)
        return super().unlink()

    # =========================================================
    # Quincena
    # =========================================================
    def _compute_pay_period_mes_caido(self, work_day: date):
        y = work_day.year
        m = work_day.month
        last_day = calendar.monthrange(y, m)[1]
        if work_day.day <= 15:
            pay_from = date(y, m, 16)
            pay_to   = date(y, m, last_day)
        else:
            nm = m + 1
            ny = y
            if nm == 13:
                nm = 1
                ny = y + 1
            pay_from = date(ny, nm, 1)
            pay_to   = date(ny, nm, 15)
        pay_date = pay_to
        label = f"{pay_from.strftime('%Y-%m-%d')} a {pay_to.strftime('%Y-%m-%d')}"
        return pay_from, pay_to, pay_date, label

    # =========================================================
    # Helpers reglas recargo
    # =========================================================
    def _float_to_time(self, hour_float):
        hh = int(hour_float)
        mm = int(round((hour_float - hh) * 60))
        if mm >= 60:
            hh += 1
            mm = 0
        if hh == 24:
            hh = 0
        return time(hh % 24, mm)

    def _get_recargo_rules(self):
        self.ensure_one()
        return self.env["payroll.recargo.rule"].sudo().search([
            ("active",     "=", True),
            ("company_id", "=", self.company_id.id),
        ], order="sequence, id")

    def _get_effective_contract_for_slot(self):
        self.ensure_one()

        employee = (self.employee_id or self.resource_id.employee_id).sudo()
        slot_start = fields.Datetime.to_datetime(self.start_datetime)
        slot_end = fields.Datetime.to_datetime(self.end_datetime)
        slot_start_date = slot_start.date() if slot_start else False
        slot_end_date = slot_end.date() if slot_end else slot_start_date

        contract = self.env["hr.contract"]
        contract_ids = getattr(employee, "contract_ids", self.env["hr.contract"]).sudo()
        if contract_ids and slot_start_date:
            matching_contracts = contract_ids.filtered(
                lambda c: (
                    (not c.date_start or c.date_start <= slot_end_date)
                    and (not c.date_end or c.date_end >= slot_start_date)
                )
            ).sorted(
                key=lambda c: (
                    c.date_start or date(1900, 1, 1),
                    c.id,
                ),
                reverse=True,
            )
            open_contracts = matching_contracts.filtered(lambda c: c.state == "open")
            contract = (open_contracts[:1] or matching_contracts[:1])

        if not contract:
            current_contract = getattr(employee, "contract_id", False)
            if current_contract:
                contract = current_contract.sudo()

        return contract

    def _get_effective_calendar_for_slot(self):
        self.ensure_one()

        employee = (self.employee_id or self.resource_id.employee_id).sudo()
        contract = self._get_effective_contract_for_slot()

        return (
            contract.resource_calendar_id
            or employee.resource_calendar_id
            or self.company_id.resource_calendar_id
        )

    def _rule_applies_to_day(self, rule, cur_day, is_sunday, is_holiday, is_public_holiday):
        if rule.date_from and cur_day < rule.date_from:
            return False
        if rule.date_to and cur_day > rule.date_to:
            return False
        if is_sunday or is_holiday:
            if (is_sunday and rule.apply_on_sunday) or (is_holiday and rule.apply_on_holiday):
                return True
            return False
        if rule.apply_on_normal:
            return True
        return False

    def _get_weekly_night_shift_limit(self):
        self.ensure_one()
        return max(0.0, float(getattr(self.company_id, "hr_night_shift_weekly_limit", 0.0) or 0.0))

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
        week_start = self._localize_safe(self._get_company_tz(), datetime.combine(week_start_date, time.min))
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
        tz = self._get_company_tz()
        for work_entry in work_entries:
            if work_entry.work_entry_type_id.id in recargo_type_ids:
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
            start_local, recargo_type_ids=recargo_type_ids
        )
        if worked_hours_before >= weekly_limit:
            return start_local, end_local

        exempt_hours_left = weekly_limit - worked_hours_before
        segment_hours = (end_local - start_local).total_seconds() / 3600.0
        if segment_hours <= exempt_hours_left:
            return None, None

        adjusted_start = start_local + timedelta(hours=exempt_hours_left)
        return adjusted_start, end_local

    def _build_expected_recargo_work_entry_vals(self):
        self.ensure_one()
        env = self.env

        if not self.employee_id or self.is_rest_day:
            return self.env["payroll.recargo.rule"], []

        rules = self._get_recargo_rules()
        if not rules:
            return rules, []

        tz = self._get_company_tz()
        start_utc = fields.Datetime.to_datetime(self.start_datetime)
        end_utc = fields.Datetime.to_datetime(self.end_datetime)
        if not start_utc or not end_utc or start_utc >= end_utc:
            return rules, []

        def to_local(dt_utc):
            if dt_utc.tzinfo is None:
                dt_utc = pytz.UTC.localize(dt_utc)
            return dt_utc.astimezone(tz)

        def day_bounds_local(d_date):
            ds = self._localize_safe(tz, datetime.combine(d_date, time(0, 0, 0)))
            de = self._localize_safe(tz, datetime.combine(d_date, time(23, 59, 59)))
            return ds, de

        def overlap(a1, a2, b1, b2):
            s = max(a1, b1)
            e = min(a2, b2)
            return (s, e) if s < e else (None, None)

        def pay_period_vals(work_day):
            pf, pt, pd, pl = self._compute_pay_period_mes_caido(work_day)
            return pf, pt, pd, pl

        start_local = to_local(start_utc)
        end_local = to_local(end_utc)
        effective_contract = self._get_effective_contract_for_slot()

        if end_local.hour == 23 and end_local.minute == 59 and end_local.second == 0:
            end_local = end_local.replace(second=59)

        cur_day = start_local.date()
        last_day = end_local.date()

        holiday_days = set()
        cal_obj = self._get_effective_calendar_for_slot()
        if cal_obj:
            range_start_local = self._localize_safe(tz, datetime.combine(cur_day, time.min))
            range_end_local = self._localize_safe(tz, datetime.combine(last_day + timedelta(days=1), time.min))
            leaves = env["resource.calendar.leaves"].sudo().search([
                ("calendar_id", "=", cal_obj.id),
                ("resource_id", "=", False),
                ("date_from", "<", range_end_local.astimezone(pytz.UTC).replace(tzinfo=None)),
                ("date_to", ">", range_start_local.astimezone(pytz.UTC).replace(tzinfo=None)),
            ])
            for lv in leaves:
                lv_start = to_local(fields.Datetime.to_datetime(lv.date_from))
                lv_end = to_local(fields.Datetime.to_datetime(lv.date_to))
                d0 = lv_start.date()
                d1 = (lv_end - timedelta(seconds=1)).date()
                d = d0
                while d <= d1:
                    holiday_days.add(d)
                    d += timedelta(days=1)

        if "hr.holidays.public.line" in env:
            hol_lines = env["hr.holidays.public.line"].sudo().search([
                ("date", ">=", cur_day),
                ("date", "<=", last_day),
            ])
            for hol in hol_lines:
                hol_date = hol.date
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
                if not self._rule_applies_to_day(rule, cur_day, is_sunday, is_holiday, lambda d: d in holiday_days):
                    continue

                t_from = self._float_to_time(rule.hour_from)
                r_start = self._localize_safe(tz, datetime.combine(cur_day, t_from))

                if rule.hour_to == 24.0:
                    r_end = self._localize_safe(tz, datetime.combine(cur_day, time(23, 59, 59)))
                else:
                    t_to = self._float_to_time(rule.hour_to)
                    r_end = self._localize_safe(tz, datetime.combine(cur_day, t_to))
                    if r_end <= r_start:
                        r_end = self._localize_safe(tz, datetime.combine(cur_day + timedelta(days=1), t_to))

                s, e = overlap(seg_start_local, seg_end_local, r_start, r_end)
                if not s or not e:
                    continue

                if (is_sunday or is_holiday) and rule.apply_on_normal:
                    continue

                if e.hour == 23 and e.minute == 59 and e.second == 0:
                    e = e.replace(second=59)

                s, e = self._apply_art_161_weekly_limit(
                    rule,
                    effective_contract,
                    s,
                    e,
                    recargo_type_ids=recargo_type_ids,
                )
                if not s or not e:
                    continue

                work_day = s.date()
                pay_from, pay_to, pay_date, pay_label = pay_period_vals(work_day)
                raw_vals.append({
                    "name": rule.work_entry_type_id.name,
                    "employee_id": self.employee_id.id,
                    "work_entry_type_id": rule.work_entry_type_id.id,
                    "contract_id": effective_contract.id if effective_contract else False,
                    "date_start": s.astimezone(pytz.UTC).replace(tzinfo=None),
                    "date_stop": e.astimezone(pytz.UTC).replace(tzinfo=None),
                    "planning_slot_id": self.id,
                    "state": "draft",
                    "company_id": self.company_id.id,
                    "duration": (e - s).total_seconds() / 3600.0,
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
                vals["planning_slot_id"],
            )
            dedup_map[key] = vals
        return rules, list(dedup_map.values())

    def _sync_recargo_work_entries(self):
        self.ensure_one()
        WE = self.env["hr.work.entry"].sudo()
        rules, expected_vals = self._build_expected_recargo_work_entry_vals()
        type_ids = rules.mapped("work_entry_type_id").ids
        if not type_ids:
            return

        existing = WE.search([
            ("planning_slot_id", "=", self.id),
            ("employee_id", "=", self.employee_id.id),
            ("work_entry_type_id", "in", type_ids),
            ("active", "=", True),
        ], order="date_start asc, id asc")

        def key_from_vals(vals):
            return (
                vals["employee_id"],
                vals["work_entry_type_id"],
                fields.Datetime.to_datetime(vals["date_start"]),
                fields.Datetime.to_datetime(vals["date_stop"]),
                vals["planning_slot_id"],
            )

        def key_from_we(we):
            return (
                we.employee_id.id,
                we.work_entry_type_id.id,
                fields.Datetime.to_datetime(we.date_start),
                fields.Datetime.to_datetime(we.date_stop),
                we.planning_slot_id.id,
            )

        expected_map = {key_from_vals(vals): vals for vals in expected_vals}
        grouped_existing = {}
        for we in existing:
            grouped_existing.setdefault(key_from_we(we), WE.browse())
            grouped_existing[key_from_we(we)] |= we

        to_remove = WE.browse()
        missing_vals = []

        for key, entries in grouped_existing.items():
            expected = expected_map.get(key)
            if not expected:
                _logger.info(
                    "[WE RECARGO] Desactivando recargo fuera de rango slot=%s we_ids=%s",
                    self.id,
                    entries.ids,
                )
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
                ).sudo().write(vals)

            duplicates = entries - survivor
            if duplicates:
                _logger.info(
                    "[WE RECARGO] Desactivando recargos duplicados slot=%s we_ids=%s",
                    self.id,
                    duplicates.ids,
                )
                to_remove |= duplicates

        for key, vals in expected_map.items():
            if key not in grouped_existing:
                missing_vals.append(vals)

        if to_remove:
            to_remove._soft_remove_entries()
        if missing_vals:
            _logger.info(
                "[WE RECARGO] Creando recargos faltantes slot=%s tipos=%s",
                self.id,
                [vals["work_entry_type_id"] for vals in missing_vals],
            )
            WE.create(missing_vals)

    # =========================================================
    # Recargos parametrizables
    # =========================================================
    def _generate_recargo_work_entries(self):
        self.ensure_one()
        WE = self.env["hr.work.entry"].sudo()
        rules, vals_list = self._build_expected_recargo_work_entry_vals()
        type_ids = rules.mapped("work_entry_type_id").ids
        if not type_ids:
            return

        self._cleanup_work_entries_for_slot(only_types=type_ids, only_draft=False, force_admin=True)
        if vals_list:
            WE.create(vals_list)
