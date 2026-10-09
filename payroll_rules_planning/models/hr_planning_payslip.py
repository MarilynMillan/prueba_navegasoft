# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time

import pytz

from odoo import api, fields, models
from odoo.osv import expression


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    planning_slot_count = fields.Integer(
        compute='_compute_planning_slot_count',
        groups="planning.group_planning_manager",
    )

    # ----------------------------------------------------------
    # Helper TZ
    # ----------------------------------------------------------
    def _get_company_tz(self):
        """
        TZ efectiva de la compañía: calendario de recursos → partner → UTC.
        Mismo orden de prioridad que el resto del módulo.
        """
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
        """
        Convierte fecha + hora naive (local) a UTC naive.

        Se usa para comparar fechas del payslip (tipo Date, en hora local)
        contra start_datetime / end_datetime (Datetime UTC en la BD).

        Sin esta conversión, Odoo ORM trata los datetimes naive como UTC,
        produciendo un corrimiento de 5 h para America/Bogota (UTC-5):

            date_from = 2026-01-01  →  00:00:00 UTC  (sin fix)
                                    →  2025-12-31 19:00 COT  ← 5 h antes del día real

            date_from = 2026-01-01  →  05:00:00 UTC  (con fix)
                                    →  2026-01-01 00:00 COT  ✓
        """
        dt_naive = datetime.combine(d, t)
        try:
            dt_local = tz.localize(dt_naive, is_dst=None)
        except Exception:
            dt_local = tz.localize(dt_naive, is_dst=False)
        return dt_local.astimezone(pytz.UTC).replace(tzinfo=None)

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------
    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_planning_slot_count(self):
        self.planning_slot_count = 0
        planning_slips = self.filtered(
            lambda p: p.contract_id.work_entry_source == 'planning'
        )
        if not planning_slips:
            return

        tz = self._get_company_tz()

        domains = []
        slip_by_employee = defaultdict(lambda: self.env['hr.payslip'])

        for slip in planning_slips:
            slip_by_employee[slip.employee_id.id] |= slip

            # FIX: convertir las fechas locales del slip a UTC antes de
            # compararlas con los campos Datetime de planning.slot.
            start_utc = self._local_date_to_utc(slip.date_from, time.min, tz)
            end_utc   = self._local_date_to_utc(slip.date_to,   time.max, tz)

            domains.append([
                ('employee_id',    '=',  slip.employee_id.id),
                ('start_datetime', '<=', fields.Datetime.to_string(end_utc)),
                ('end_datetime',   '>=', fields.Datetime.to_string(start_utc)),
            ])

        domain = expression.AND([
            [('state', '=', 'published')],
            expression.OR(domains),
        ])

        read_group = self.env['planning.slot']._read_group(
            domain,
            groupby=['employee_id', 'start_datetime:day'],
            aggregates=['__count'],
        )

        # El _read_group ya devuelve start_datetime en UTC con tzinfo;
        # convertimos a fecha local del empleado para comparar con date_from/date_to.
        for employee, start_datetime_utc, count in read_group:
            slips = slip_by_employee[employee.id]
            emp_tz = pytz.timezone(employee.tz) if employee.tz else tz
            start_date_employee = start_datetime_utc.astimezone(emp_tz).date()
            for slip in slips:
                if slip.date_from <= start_date_employee <= slip.date_to:
                    slip.planning_slot_count += count

    # ----------------------------------------------------------
    # Acción
    # ----------------------------------------------------------
    def action_open_planning_slots(self):
        self.ensure_one()

        # FIX: mismo problema que en _compute — date_from/date_to son fechas
        # locales; hay que convertirlas a UTC para filtrar Datetime correctamente.
        tz = self._get_company_tz()
        start_utc = self._local_date_to_utc(self.date_from, time.min, tz)
        end_utc   = self._local_date_to_utc(self.date_to,   time.max, tz)

        action = self.employee_id.action_view_planning()
        action['domain'] = expression.AND([
            action['domain'],
            [
                ('state',          '=',  'published'),
                ('start_datetime', '<=', fields.Datetime.to_string(end_utc)),
                ('end_datetime',   '>=', fields.Datetime.to_string(start_utc)),
            ],
        ])
        action['context']['default_scale'] = 'month'
        return action