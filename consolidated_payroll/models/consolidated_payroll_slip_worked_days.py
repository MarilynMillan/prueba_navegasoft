from odoo import api, fields, models


class ConsolidatedPayrollSlipWorkedDays(models.Model):
    _name = 'consolidated.payroll.slip.worked.days'
    _description = 'Días trabajados recibo de nómina'
    _order = 'payslip_id, sequence'

    name = fields.Char(compute='_compute_name', store=True, string='Descripción', readonly=True)
    payslip_id = fields.Many2one('consolidated.payroll.slip', string='Recibo de nómina', required=True,  index=True, readonly=True)#ondelete='cascade',
    sequence = fields.Integer(required=True, index=True, default=10, readonly=True)
    code = fields.Char(string='Code', related='work_entry_type_id.code', readonly=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Tipo', required=True, readonly=True)
    number_of_days = fields.Float(string='Número de días')
    number_of_hours = fields.Float(string='Número de horas')
    amount = fields.Monetary(string='Importe', compute='_compute_amount', store=True, copy=True, readonly=True)
    contract_id = fields.Many2one(related='payslip_id.contract_id', string='Contract', readonly=True)
    currency_id = fields.Many2one('res.currency', related='payslip_id.currency_id', readonly=True)
    is_paid = fields.Boolean(readonly=True)
    
    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        for worked_days in self:
            if not worked_days.contract_id or worked_days.code == 'OUT':
                worked_days.amount = 0
                continue
            if worked_days.payslip_id.wage_type == "hourly":
                worked_days.amount = worked_days.payslip_id.contract_id.hourly_wage * worked_days.number_of_hours if worked_days.is_paid else 0
            else:
                worked_days.amount = worked_days.payslip_id.contract_id.contract_wage * worked_days.number_of_hours / (worked_days.payslip_id.sum_worked_hours or 1) if worked_days.is_paid else 0

    @api.depends('work_entry_type_id')
    def _compute_name(self):
        for worked_days in self:
            worked_days.name = worked_days.work_entry_type_id.name
