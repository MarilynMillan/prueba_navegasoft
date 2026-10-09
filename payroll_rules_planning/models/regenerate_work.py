# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time
import pytz
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class HrWorkEntryRegenerationWizard(models.TransientModel):
    _inherit = "hr.work.entry.regeneration.wizard"

    def _get_wizard_tz(self):
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

    def _local_date_to_utc(self, d, t, tz):
        dt_naive = datetime.combine(d, t)
        try:
            dt_local = tz.localize(dt_naive, is_dst=None)
        except Exception:
            dt_local = tz.localize(dt_naive, is_dst=False)
        return dt_local.astimezone(pytz.UTC).replace(tzinfo=None)

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

    def _match_validated_worked_time_leave(self, rec):
        if not rec or not rec.employee_id or not rec.date_start or not rec.date_stop:
            return self.env["hr.leave"]
        leave = self.env["hr.work.entry"].sudo()._match_worked_time_leave_for_entry(rec)
        if not leave:
            return self.env["hr.leave"]
        return leave.filtered(
            lambda l: l.state in ("confirm", "validate")
            and l.holiday_status_id
            and l.holiday_status_id.time_type == "other"
        )[:1]

    def _normalize_worked_time_entries_in_range(self, employee_ids, dt_from, dt_to):
        WorkEntry = self.env["hr.work.entry"].sudo()
        entries = WorkEntry.search([
            ("employee_id", "in", employee_ids),
            ("date_start", "<=", dt_to),
            ("date_stop", ">=", dt_from),
            ("active", "=", True),
        ])
        if entries:
            entries._normalize_worked_time_leave_entries()

    def _ensure_validated_worked_time_leaves_in_range(self, employee_ids, dt_from, dt_to):
        leaves = self.env["hr.leave"].sudo().search([
            ("employee_id", "in", employee_ids),
            ("state", "=", "validate"),
            ("holiday_status_id.time_type", "=", "other"),
            ("date_from", "<=", dt_to),
            ("date_to", ">=", dt_from),
        ])
        if leaves:
            leaves._ensure_validated_worked_time_work_entries()
            leaves._cleanup_planning_work_entries_during_leave()
            leaves._recheck_work_entry_conflicts()

    def _ensure_validated_leave_entries_in_range(self, employee_ids, dt_from, dt_to):
        leaves = self.env["hr.leave"].sudo().search([
            ("employee_id", "in", employee_ids),
            ("state", "=", "validate"),
            ("holiday_status_id.time_type", "=", "leave"),
            ("date_from", "<=", dt_to),
            ("date_to", ">=", dt_from),
        ])
        if leaves:
            leaves._ensure_validated_leave_work_entries()
            leaves._cleanup_planning_work_entries_during_leave()
            leaves._recheck_work_entry_conflicts()

    def regenerate_work_entries(self):
        # ---------------------------------------------------------------
        # Paso 1: Nativo — regenera WEs de contrato/calendario.
        #         Crea WEs SIN planning_slot_id que solapan con los slots.
        # ---------------------------------------------------------------
        res = super().regenerate_work_entries()

        PlanningSlot = self.env["planning.slot"].sudo()

        for wiz in self:
            if not wiz.employee_ids or not wiz.date_from or not wiz.date_to:
                continue

            # FIX TZ: convertir fechas locales del wizard → UTC
            tz = self._get_wizard_tz()
            dt_from = self._local_date_to_utc(wiz.date_from, time.min, tz)
            dt_to   = self._local_date_to_utc(wiz.date_to,   time.max, tz)

            # ---------------------------------------------------------------
            # Paso 2: Limpiar WEs sin planning_slot_id en días con slots.
            #         Esto elimina las WEs parciales del paso 1 (ej: 06:00-08:00
            #         en días festivos con slots).
            # ---------------------------------------------------------------
            self._cleanup_festivo_we_conflicting_with_slots(
                employee_ids=wiz.employee_ids.ids,
                dt_from=dt_from,
                dt_to=dt_to,
            )

            # ---------------------------------------------------------------
            # Paso 3: Regenerar WEs de slots APROBADOS.
            #
            #   Para cada slot aprobado (approval_state='approved'):
            #     a) Limpiar TODAS las WEs del slot (asistencia + recargos).
            #     b) Resetear flags de idempotencia.
            #     c) Crear WE de Asistencia con planning_slot_id cubriendo
            #        el rango COMPLETO del turno (no solo la intersección
            #        con el horario del contrato).
            #     d) Crear WEs de recargos.
            #
            #   Buscar también por state='published' por compatibilidad
            #   con slots aprobados antes del campo approval_state.
            # ---------------------------------------------------------------
            slots_aprobados = PlanningSlot.search([
                ("employee_id",    "in", wiz.employee_ids.ids),
                ("approval_state", "=",  "approved"),
                ("is_rest_day",    "=",  False),
                ("start_datetime", "<=", dt_to),
                ("end_datetime",   ">=", dt_from),
            ])

            _logger.info(
                "[WIZARD REGEN] %s slots aprobados a regenerar "
                "(empleados=%s rango_utc=%s..%s)",
                len(slots_aprobados), wiz.employee_ids.ids, dt_from, dt_to,
            )

            for slot in slots_aprobados:
                # Limpiar TODAS las WEs del slot (draft, validated, conflict)
                slot._cleanup_work_entries_for_slot(
                    only_types=None,
                    only_draft=False,
                    force_admin=True,
                )
                # También limpiar WEs nativas del paso 1 sin planning_slot_id
                # que puedan existir en el rango de este slot
                self._cleanup_we_without_slot_for_range(
                    employee_id=slot.employee_id.id,
                    start_utc=slot.start_datetime,
                    end_utc=slot.end_datetime,
                )
                # Resetear flags
                slot.sudo().write({
                    "work_entries_generated": False,
                    "recargos_generated":     False,
                })
                # Crear WE de Asistencia con rango completo + planning_slot_id
                slot._ensure_work_entries_once()
                # Crear WEs de recargos
                slot._generate_recargo_work_entries_once()

            # ---------------------------------------------------------------
            # Paso 4: Segunda pasada de limpieza por si quedaron WEs
            #         residuales sin planning_slot_id (del fallback action_send).
            # ---------------------------------------------------------------
            self._cleanup_festivo_we_conflicting_with_slots(
                employee_ids=wiz.employee_ids.ids,
                dt_from=dt_from,
                dt_to=dt_to,
            )

            self._ensure_validated_leave_entries_in_range(
                employee_ids=wiz.employee_ids.ids,
                dt_from=dt_from,
                dt_to=dt_to,
            )

            self._ensure_validated_worked_time_leaves_in_range(
                employee_ids=wiz.employee_ids.ids,
                dt_from=dt_from,
                dt_to=dt_to,
            )

            self._normalize_worked_time_entries_in_range(
                employee_ids=wiz.employee_ids.ids,
                dt_from=dt_from,
                dt_to=dt_to,
            )

            self.env["hr.work.entry"].sudo()._sync_generated_recargo_work_entries_for_range(
                employee_ids=wiz.employee_ids.ids,
                dt_from=dt_from,
                dt_to=dt_to,
            )

        return res

    def _cleanup_we_without_slot_for_range(self, employee_id, start_utc, end_utc):
        """
        Elimina WEs sin planning_slot_id del empleado que solapan
        exactamente con el rango del slot. Sirve para limpiar WEs nativas
        parciales (ej: 06:00-08:00) antes de crear la WE correcta (06:00-14:00).
        """
        if not start_utc or not end_utc:
            return
        WE = self.env["hr.work.entry"].sudo()
        candidates = WE.search([
            ("employee_id",      "=",    employee_id),
            ("planning_slot_id", "=",    False),
            ("date_start",       ">=",   start_utc),
            ("date_stop",        "<=",   end_utc),
            ("state",            "in",   ["draft", "conflict", "validated"]),
        ])
        candidates = candidates.filtered(
            lambda w: not self._match_validated_worked_time_leave(w) and not self._is_employee_requested_absence(w)
        )
        if candidates:
            conflict_ones = candidates.filtered(lambda w: w.state == "conflict")
            if conflict_ones:
                conflict_ones.write({"state": "draft"})
            _logger.info(
                "[WIZARD CLEANUP RANGE] Eliminando %s WEs nativas del rango %s→%s emp=%s",
                len(candidates), start_utc, end_utc, employee_id,
            )
            candidates._soft_remove_entries()

    def _is_employee_requested_absence(self, rec):
        if not rec.leave_id:
            return False
        leave = rec.leave_id
        holiday_type = getattr(leave, "holiday_type", None)
        if holiday_type == "employee":
            return True
        if holiday_type in ("company", "department", "category"):
            return False
        if holiday_type is None and leave.employee_id and leave.employee_id == rec.employee_id:
            return True
        return False

    def _cleanup_festivo_we_conflicting_with_slots(self, employee_ids, dt_from, dt_to):
        """
        Elimina WEs sin planning_slot_id en días con slots activos.
        Estados cubiertos: draft, conflict y validated.
        dt_from / dt_to ya están en UTC.
        """
        WE = self.env["hr.work.entry"].sudo()

        candidates = WE.search([
            ("employee_id",      "in", employee_ids),
            ("planning_slot_id", "=",  False),
            ("date_start",       "<=", dt_to),
            ("date_stop",        ">=", dt_from),
            ("state",            "in", ["draft", "conflict", "validated"]),
        ])

        _logger.info(
            "[WIZARD CLEANUP] Candidatas: %s WEs (empleados=%s rango_utc=%s..%s)",
            len(candidates), employee_ids, dt_from, dt_to,
        )

        if not candidates:
            return

        to_unlink = WE

        for rec in candidates:
            if not rec.date_start or not rec.date_stop:
                continue

            if self._is_employee_requested_absence(rec):
                continue

            worked_time_leave = self._match_validated_worked_time_leave(rec)
            if worked_time_leave:
                _logger.info(
                    "[WIZARD CLEANUP] Preservando WE id=%s emp=%s por Worked Time leave_id=%s",
                    rec.id,
                    rec.employee_id.name,
                    worked_time_leave.id,
                )
                continue

            tz = self._get_employee_tz(rec.employee_id)
            date_start_dt = rec.date_start
            if isinstance(date_start_dt, datetime):
                date_start_aware = (
                    pytz.UTC.localize(date_start_dt)
                    if date_start_dt.tzinfo is None
                    else date_start_dt
                )
            else:
                date_start_aware = pytz.UTC.localize(
                    datetime.combine(date_start_dt, time.min)
                )

            local_date = date_start_aware.astimezone(tz).date()

            day_start_utc = tz.localize(
                datetime.combine(local_date, time.min)
            ).astimezone(pytz.UTC).replace(tzinfo=None)

            day_end_utc = tz.localize(
                datetime.combine(local_date + timedelta(days=1), time.min)
            ).astimezone(pytz.UTC).replace(tzinfo=None)

            planning_slot = self.env["planning.slot"].sudo().search([
                ("employee_id",    "=", rec.employee_id.id),
                ("is_rest_day",    "=", False),
                ("start_datetime", "<", day_end_utc),
                ("end_datetime",   ">", day_start_utc),
            ], limit=1)

            if planning_slot:
                _logger.info(
                    "[WIZARD CLEANUP] Eliminando WE id=%s tipo=%s emp=%s "
                    "fecha_local=%s state=%s — slot id=%s (leave_id=%s).",
                    rec.id,
                    rec.work_entry_type_id.code or rec.work_entry_type_id.name,
                    rec.employee_id.name, local_date, rec.state,
                    planning_slot.id,
                    rec.leave_id.id if rec.leave_id else "none",
                )
                to_unlink |= rec

        if to_unlink:
            _logger.info(
                "[WIZARD CLEANUP] Total desactivadas: %s WEs (empleados=%s rango_utc=%s..%s)",
                len(to_unlink), employee_ids, dt_from, dt_to,
            )
            to_unlink._soft_remove_entries()
