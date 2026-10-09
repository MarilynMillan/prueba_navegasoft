from odoo import models, fields, api,_
from datetime import date
from dateutil.relativedelta import relativedelta

from collections import defaultdict
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round
class ConsolidatePayrollSlip(models.Model):
    _name = 'consolidated.payroll.slip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidado de nómina recibos'

    consolidated_payroll_id = fields.Many2one('consolidated.payroll', string="Consolidado")
    assoc_slips = fields.One2many('consolidated.payroll.slip.assoc', 'consolidated_id', string="Recibos de nómina asociados", readonly=True)
    name = fields.Char(string='Consolidado de nómina', compute="_compute_name", store=True, readonly=True)
    number = fields.Char(
        string='Referencia', readonly=True, copy=False)
    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True, readonly=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), '|', ('active', '=', True), ('active', '=', False)]")
    department_id = fields.Many2one('hr.department', string='Departamento', related='employee_id.department_id', readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Posición', related='employee_id.job_id', readonly=True, store=True)
    date_from = fields.Date(
        string='Desde', required=True, readonly=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(
        string='Hasta', required=True, readonly=True,
        precompute=True, compute="_compute_date_to", store=True)
    contract_id = fields.Many2one(
        'hr.contract', string='Contrato', readonly=True,
        domain="[('id', 'in', contract_domain_ids)]",
        compute='_compute_contract_id', store=True)
    contract_domain_ids = fields.Many2many('hr.contract', compute='_compute_contract_domain_ids')
    company_id = fields.Many2one(
        'res.company', string='Compañia', copy=False, required=True,
        compute='_compute_company_id', store=True, readonly=True,
        default=lambda self: self.env.company)
    country_id = fields.Many2one(
        'res.country', string='País',
        related='company_id.country_id', readonly=True
    )
    country_code = fields.Char(related='country_id.code', depends=['country_id'], readonly=True)
    basic_wage = fields.Monetary(string="Salario básico", readonly=True)
    net_wage = fields.Monetary(string="Salario neto", readonly=True)
    currency_id = fields.Many2one(related='contract_id.currency_id', readonly=True)
    line_ids = fields.One2many(
        'consolidated.payroll.slip.line', 'slip_id', string='Líneas recibo de nómina', readonly=True)
    worked_days_line_ids = fields.One2many(
        'consolidated.payroll.slip.worked.days', 'payslip_id', string='Días trabajados recibo de nómina')
    input_line_ids = fields.One2many(
        'consolidated.payroll.slip.input', 'payslip_id', string='Otras entradas recibo de nómina', readonly=True)
    sum_worked_hours = fields.Float(compute='_compute_worked_hours', store=True, readonly=True)
    struct_id = fields.Many2one(
        'hr.payroll.structure', string='Estructura',
        compute='_compute_struct_id', store=True, readonly=True)
    struct_type_id = fields.Many2one('hr.payroll.structure.type', related='struct_id.type_id', readonly=True)
    wage_type = fields.Selection(related='struct_type_id.wage_type', readonly=True)
    slip_assoc_count = fields.Integer(compute="_compute_slip_assoc_count")
    consolidated_id = fields.Many2one('consolidated.payroll.slip', string='Consolidado Rectificado', readonly=True)
    credit_type=fields.Selection([('delete','Eliminar'),('fix','Modificar')],string='Tipo de crédito',default='delete',required=True)
    @api.depends('number')
    @api.depends('number')
    def _compute_name(self):
        for payroll in self:
            payroll.name = 'Consolidado %(number)s' % {'number': payroll.number}

    @api.depends('date_from')
    def _compute_date_to(self):
        next_month = relativedelta(months=+1, day=1, days=-1)
        for payslip in self:
            payslip.date_to = payslip.date_from + next_month

    @api.depends('company_id', 'employee_id', 'date_from', 'date_to')
    def _compute_contract_domain_ids(self):
        for payslip in self:
            payslip.contract_domain_ids = self.env['hr.contract'].search([
                ('company_id', '=', payslip.company_id.id),
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '!=', 'cancel'),
                ('date_start', '<=', payslip.date_to),
                '|',
                ('date_end', '>=', payslip.date_from),
                ('date_end', '=', False)])
    
    @api.depends('worked_days_line_ids.number_of_hours')
    def _compute_worked_hours(self):
        for payslip in self:
            payslip.sum_worked_hours = sum([line.number_of_hours for line in payslip.worked_days_line_ids])

    @api.depends('contract_id')
    def _compute_struct_id(self):
        for slip in self.filtered(lambda p: not p.struct_id):
            slip.struct_id = slip.contract_id.structure_type_id.default_struct_id

    def action_open_slips_assoc(self):
        self.ensure_one()
        slips_ids = []
        for assoc_slip in self.assoc_slips:
            slips_ids.append(assoc_slip.slip_id.id) 
    
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "list"], [False, "form"]],
            "domain": [['id', 'in', slips_ids]],
            "context": {
                "create": False,
                "delete": False,
                "duplicate": False
            },
            "name": "Recibos de nómina asociados",
        }

    def _compute_slip_assoc_count(self):
        for slip in self:
            slip.slip_assoc_count = len(slip.assoc_slips)

    def _get_source_payslips(self):
        """Obtiene los hr.payslip fuente vía consolidated.payroll.slip.assoc."""
        Assoc = self.env['consolidated.payroll.slip.assoc'].sudo()
        self.ensure_one()
        assoc = Assoc.search([('consolidated_id', '=', self.id)])
        if not assoc:
            return self.env['hr.payslip']
        return self.env['hr.payslip'].sudo().browse(assoc.mapped('slip_id'))

    def _rebuild_from_sources(self, sources):
        """
        Reconstruye (re-agrupa) líneas, días trabajados e inputs del consolidado
        a partir de un conjunto de hr.payslip `sources`.
        """
        self.ensure_one()
        if not sources:
            raise ValidationError(_("No se encontraron recibos fuente para este consolidado."))

        # 1) borrar detalle actual
        #   Ojo: nombres de campos asumidos; ajusta si difieren en tu modelo
        self.line_ids.sudo().unlink()
        self.worked_days_line_ids.sudo().unlink()
        self.input_line_ids.sudo().unlink()

        # 2) agrupar líneas por code
        grouped_lines = defaultdict(lambda: {
            'name': '',
            'code': '',
            'sequence': 0,
            'salary_rule_id': False,
            'category_id': False,
            'contract_id': False,
            'employee_id': False,
            'rate': 0.0,
            'amount': 0.0,
            'quantity': 0.0,
            'total': 0.0,
            'appears_on_payslip': True,
            'company_id': False,
            'currency_id': False,
            'date_from': self.date_from,
            'date_to': self.date_to,
        })

        basic_wage = 0.0
        net_wage = 0.0

        for slip in sources.ids:
            basic_wage += slip.basic_wage
            net_wage += slip.net_wage
            for line in slip.line_ids:
                k = line.salary_rule_id.code or line.code or line.name
                b = grouped_lines[k]
                # Conserva primera metadata vista
                if not b['name']:
                    b['name'] = line.name
                    b['code'] = line.code
                    b['sequence'] = line.sequence
                    b['salary_rule_id'] = line.salary_rule_id.id
                    b['category_id'] = line.category_id.id
                    b['contract_id'] = line.contract_id.id
                    b['employee_id'] = line.employee_id.id
                    b['appears_on_payslip'] = line.appears_on_payslip
                    b['company_id'] = line.company_id.id
                    b['currency_id'] = line.currency_id.id
                # Sumas
                b['quantity'] += line.quantity
                b['amount'] += line.amount
                b['rate'] += line.rate   # luego promediamos
                b['total'] += line.total

        # Promediar rate por regla
        for k, v in grouped_lines.items():
            # Para evitar dividir entre cero, usamos 1 como mínimo
            count = len([1 for s in sources.ids for l in s.line_ids if (l.salary_rule_id.code or l.code or l.name) == k]) or 1
            v['rate'] = v['rate'] / count

        # 3) crear líneas consolidadas
        Line = self.env['consolidated.payroll.slip.line'].sudo()
        for values in grouped_lines.values():
            vals = dict(values)
            vals['slip_id'] = self.id
            Line.create(vals)

        # 4) agrupar días trabajados por tipo
        grouped_days = defaultdict(lambda: {
            'name': '',
            'code': '',
            'sequence': 0,
            'work_entry_type_id': False,
            'number_of_days': 0.0,
            'number_of_hours': 0.0,
            'contract_id': False,
            'is_paid': False,
            'currency_id': False,
        })
        for slip in sources.ids:
            for wd in slip.worked_days_line_ids:
                k = wd.work_entry_type_id.id or wd.code or wd.name
                b = grouped_days[k]
                if not b['name']:
                    b['name'] = wd.name
                    b['code'] = wd.code
                    b['sequence'] = wd.sequence
                    b['work_entry_type_id'] = wd.work_entry_type_id.id
                    b['contract_id'] = wd.contract_id.id
                    b['is_paid'] = wd.is_paid
                    b['currency_id'] = wd.currency_id.id
                b['number_of_days'] +=  float_round(wd.number_of_days, precision_digits=2)
                b['number_of_hours'] += float_round(wd.number_of_hours, precision_digits=2)

        Worked = self.env['consolidated.payroll.slip.worked.days'].sudo()
        for values in grouped_days.values():
            vals = dict(values)
            vals['payslip_id'] = self.id
            Worked.create(vals)

        # 5) agrupar inputs por tipo
        grouped_inputs = defaultdict(lambda: {
            'name': '',
            'code': '',
            'sequence': 0,
            'input_type_id': False,
            'amount': 0.0,
            'contract_id': False,
        })
        for slip in sources.ids:
            for inp in slip.input_line_ids:
                k = inp.input_type_id.id or inp.code or inp.name
                b = grouped_inputs[k]
                if not b['name']:
                    b['name'] = inp.name
                    b['code'] = inp.code
                    b['sequence'] = inp.sequence
                    b['input_type_id'] = inp.input_type_id.id
                    b['contract_id'] = inp.contract_id.id
                b['amount'] += inp.amount

        Input = self.env['consolidated.payroll.slip.input'].sudo()
        for values in grouped_inputs.values():
            vals = dict(values)
            vals['payslip_id'] = self.id
            Input.create(vals)

        # 6) actualizar totales del consolidado
        self.sudo().write({
            'basic_wage': basic_wage,
            'net_wage': net_wage,
        })

    def action_recalculate(self):
        """
        Acción masiva desde la vista de lista.
        Recalcula cada consolidado seleccionando sus hr.payslip fuente y
        re-agrupando todo el detalle.
        """
        for rec in self:
            sources = rec._get_source_payslips()
            rec._rebuild_from_sources(sources)

        # Notificación visual opcional
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recalculo completado'),
                'message': _('Se recalcularon %s consolidado(s).') % len(self),
                'type': 'success',
                'sticky': False,
            }
        }

    def _sum_from_sources(self, sources):
        """Suma básicos para encabezado de slip a partir de sources (hr.payslip records)."""
        basic_wage = 0.0
        net_wage = 0.0
        for s in sources.ids:
            basic_wage += (s.basic_wage or 0.0)
            net_wage += (s.net_wage or 0.0)
        return basic_wage, net_wage

    def _group_detail_from_sources(self, sources, date_from, date_to):
        """Agrupa líneas, días e inputs a partir de sources."""
        # 1) líneas
        grouped_lines = defaultdict(lambda: {
            'name': '',
            'code': '',
            'sequence': 0,
            'salary_rule_id': False,
            'category_id': False,
            'contract_id': False,
            'employee_id': False,
            'rate': 0.0,
            'amount': 0.0,
            'quantity': 0.0,
            'total': 0.0,
            'appears_on_payslip': True,
            'company_id': False,
            'currency_id': False,
            'date_from': date_from,
            'date_to': date_to,
        })
        # 2) días trabajados
        grouped_days = defaultdict(lambda: {
            'name': '',
            'code': '',
            'sequence': 0,
            'work_entry_type_id': False,
            'number_of_days': 0.0,
            'number_of_hours': 0.0,
            'contract_id': False,
            'is_paid': False,
            'currency_id': False,
        })
        # 3) inputs
        grouped_inputs = defaultdict(lambda: {
            'name': '',
            'code': '',
            'sequence': 0,
            'input_type_id': False,
            'amount': 0.0,
            'contract_id': False,
        })

        # recorrer sources (records, no .ids)
        for slip in sources.ids:
            # líneas
            for line in slip.line_ids:
                k = line.salary_rule_id.code or line.code or line.name
                b = grouped_lines[k]
                if not b['name']:
                    b['name'] = line.name
                    b['code'] = line.code
                    b['sequence'] = line.sequence
                    b['salary_rule_id'] = line.salary_rule_id.id
                    b['category_id'] = line.category_id.id
                    b['contract_id'] = line.contract_id.id
                    b['employee_id'] = line.employee_id.id
                    b['appears_on_payslip'] = line.appears_on_payslip
                    b['company_id'] = line.company_id.id
                    b['currency_id'] = line.currency_id.id
                b['quantity'] += (line.quantity or 0.0)
                b['amount'] += (line.amount or 0.0)
                b['rate'] += (line.rate or 0.0)   # se promedia más abajo
                b['total'] += (line.total or 0.0)

            # días
            for wd in slip.worked_days_line_ids:
                k = wd.work_entry_type_id.id or wd.code or wd.name
                b = grouped_days[k]
                if not b['name']:
                    b['name'] = wd.name
                    b['code'] = wd.code
                    b['sequence'] = wd.sequence
                    b['work_entry_type_id'] = wd.work_entry_type_id.id
                    b['contract_id'] = wd.contract_id.id
                    b['is_paid'] = wd.is_paid
                    b['currency_id'] = wd.currency_id.id
                b['number_of_days'] += float_round(wd.number_of_days or 0.0, precision_digits=2)
                b['number_of_hours'] += float_round(wd.number_of_hours or 0.0, precision_digits=2) 

            # inputs
            for inp in slip.input_line_ids:
                k = inp.input_type_id.id or inp.code or inp.name
                b = grouped_inputs[k]
                if not b['name']:
                    b['name'] = inp.name
                    b['code'] = inp.code
                    b['sequence'] = inp.sequence
                    b['input_type_id'] = inp.input_type_id.id
                    b['contract_id'] = inp.contract_id.id
                b['amount'] += (inp.amount or 0.0)

        # Promedio de rate por clave de regla
        for k, v in grouped_lines.items():
            count = 0
            for slip in sources.ids:
                for line in slip.line_ids:
                    kk = line.salary_rule_id.code or line.code or line.name
                    if kk == k:
                        count += 1
            v['rate'] = v['rate'] / (count or 1)

        return grouped_lines, grouped_days, grouped_inputs

    def _get_source_payslips(self):
        """Obtiene los hr.payslip fuente vía consolidated.payroll.slip.assoc."""
        Assoc = self.env['consolidated.payroll.slip.assoc'].sudo()
        self.ensure_one()
        assoc = Assoc.search([('consolidated_id', '=', self.id)])
        if not assoc:
            return self.env['hr.payslip']
        return self.env['hr.payslip'].sudo().browse(assoc.mapped('slip_id'))

    def action_consolidate_into_new_document(self):
        """
        Acción de servidor ejecutada sobre uno o varios consolidated.payroll.slip.
        Crea un NUEVO consolidated.payroll y, por cada slip seleccionado,
        crea un NUEVO consolidated.payroll.slip re-agrupando sus hr.payslip fuente.
        Copia campos clave y enlaza con el slip original vía 'consolidated_id'.
        """
        #self.ensure_one()
        slips = self.browse(self.env.context.get('active_ids', []) or self.ids)
        if not slips:
            raise ValidationError(_("No hay registros seleccionados."))

        # Validaciones de consistencia: misma compañía y mismo período
        companies = set(slips.mapped('company_id').ids)
        if len(companies) > 1:
            raise ValidationError(_("Debe seleccionar slips de la misma compañía."))

        # Tomamos el consolidado origen del primer slip para heredar metadatos del encabezado
        first_cp = slips[0].consolidated_payroll_id
        if not first_cp:
            raise ValidationError(_("Los slips seleccionados no pertenecen a un consolidado válido."))

        # Opcional: validar mismo mes/año/fecha de pago
        months = set(slips.mapped('consolidated_payroll_id.month'))
        years = set(slips.mapped('consolidated_payroll_id.year'))
        paydates = set(slips.mapped('consolidated_payroll_id.payment_date'))
        if len(months) > 1 or len(years) > 1 or len(paydates) > 1:
            raise ValidationError(_("Todos los slips deben pertenecer al mismo período (mes/año) y fecha de pago."))

        Consolidated = self.env['consolidated.payroll'].sudo()

        # Crear nuevo encabezado
        new_vals = {
            'name': _("%s - Rectificación (desde slips)") % (first_cp.name or ''),
            'state': 'draft',
            'month': first_cp.month,
            'year': first_cp.year,
            'payment_date': first_cp.payment_date,
            'company_id': first_cp.company_id.id,
            'rectified': True,
            # si tu modelo usa inicio/fin de periodo
            'start_date': getattr(first_cp, 'start_date', False),
            'end_date': getattr(first_cp, 'end_date', False),
        }
        new_cp = Consolidated.create(new_vals)

        # Helpers de modelos detalle
        Line = self.env['consolidated.payroll.slip.line'].sudo()
        Worked = self.env['consolidated.payroll.slip.worked.days'].sudo()
        Input = self.env['consolidated.payroll.slip.input'].sudo()
        Assoc = self.env['consolidated.payroll.slip.assoc'].sudo()

        # Crear cada nuevo slip a partir del seleccionado
        for origin_slip in slips:
            sources = origin_slip._get_source_payslips()
            if not sources:
                # Si no hay fuentes, saltamos este empleado
                continue

            # Totales y agrupaciones
            basic_wage, net_wage = self._sum_from_sources(sources)
            date_from = getattr(new_cp, 'start_date', origin_slip.date_from)
            date_to = getattr(new_cp, 'end_date', origin_slip.date_to)
            g_lines, g_days, g_inputs = self._group_detail_from_sources(sources, date_from, date_to)

            # Secuencia
            number = self.env['ir.sequence'].next_by_code('consolidated.payroll.slip')

            # Construcción de vals copiando campos del origin_slip
            slip_vals = {
                'number': number,
                'employee_id': origin_slip.employee_id.id,
                'department_id': origin_slip.department_id.id,
                'job_id': origin_slip.job_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'contract_id': origin_slip.contract_id.id,
                'company_id': origin_slip.company_id.id,
                'country_id': origin_slip.country_id.id,
                'country_code': origin_slip.country_code,
                'basic_wage': basic_wage,
                'net_wage': net_wage,
                'currency_id': origin_slip.currency_id.id,
                'consolidated_payroll_id': new_cp.id,
                'struct_id': origin_slip.struct_id.id,
                'struct_type_id': origin_slip.struct_type_id.id,
                'wage_type': origin_slip.wage_type,
                'fecha_pago': new_cp.payment_date or origin_slip.fecha_pago,
                # Enlace al slip anterior:
                'consolidated_id': origin_slip.id,
                # Campos especiales que pediste conservar:
                'cune': origin_slip.cune,
                'id_plataforma': origin_slip.id_plataforma,
                'NIT': origin_slip.NIT,
                'DV': origin_slip.DV,
                'OtrosNombres': origin_slip.OtrosNombres,
                'PrimerNombre': origin_slip.PrimerNombre,
                'PrimerApellido': origin_slip.PrimerApellido,
                'SegundoApellido': origin_slip.SegundoApellido,
                'Algoritmo': origin_slip.Algoritmo,
                'tipoXML': origin_slip.tipoXML,
                'transaccionID': origin_slip.transaccionID,
               'credit_note':True,
            }
            new_slip = self.env['consolidated.payroll.slip'].sudo().create(slip_vals)

            # Asociaciones consolidated.payroll.slip.assoc
            assoc_recs = Assoc.create([
                {'consolidated_id': origin_slip.id, 'slip_id': s.id}
                for s in sources.ids
            ])
            # Si tu campo M2M se llama 'assoc_slips', ajusta aquí:
            if hasattr(new_slip, 'assoc_slips'):
                new_slip.write({'assoc_slips': [(6, 0, assoc_recs.ids)]})

            # Detalle: líneas
            for values in g_lines.values():
                vals = dict(values)
                vals['slip_id'] = new_slip.id
                Line.create(vals)

            # Detalle: días trabajados
            for values in g_days.values():
                vals = dict(values)
                vals['payslip_id'] = new_slip.id
                Worked.create(vals)

            # Detalle: inputs
            for values in g_inputs.values():
                vals = dict(values)
                vals['payslip_id'] = new_slip.id
                Input.create(vals)

        # Cerrar el nuevo consolidado
        new_cp.write({'state': 'done'})

        # Abrir el nuevo consolidado
        return {
            "type": "ir.actions.act_window",
            "res_model": "consolidated.payroll",
            "views": [[False, "form"]],
            "res_id": new_cp.id,
            "target": "current",
            "name": _("Consolidado de nómina (nuevo)"),
        }