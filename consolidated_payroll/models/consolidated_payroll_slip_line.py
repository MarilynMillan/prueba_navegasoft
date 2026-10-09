from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ConsolidatedPayrollSlipLine(models.Model):
    _name = 'consolidated.payroll.slip.line'
    _description = 'Líneas recibo de nómina'
    _order = 'contract_id, sequence, code'

    name = fields.Char(required=True, string="Nombre", readonly=True)
    sequence = fields.Integer(required=True, index=True, default=5, readonly=True)
    code = fields.Char(required=True, string="Código", readonly=True)
    slip_id = fields.Many2one('consolidated.payroll.slip', string='Recibo de nómina', required=True,  readonly=True)#ondelete='cascade',
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Regla', required=True, readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato', required=True, index=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, readonly=True)
    rate = fields.Float(string='Tasa (%)', digits='Payroll Rate', default=100.0, readonly=True)
    amount = fields.Monetary(string="Importe", readonly=True)
    quantity = fields.Float(digits='Payroll', string="Cantidad", default=1.0, readonly=True)
    total = fields.Monetary(string='Total', readonly=True)
    appears_on_payslip = fields.Boolean(related='salary_rule_id.appears_on_payslip', readonly=True)
    category_id = fields.Many2one(string="Categoría", related='salary_rule_id.category_id', readonly=True, store=True)
    date_from = fields.Date(string='Desde', related="slip_id.date_from", store=True, readonly=True)
    date_to = fields.Date(string='Hasta', related="slip_id.date_to", store=True, readonly=True)
    company_id = fields.Many2one(related='slip_id.company_id', readonly=True)
    currency_id = fields.Many2one('res.currency', related='slip_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['consolidated.payroll.slip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get('contract_id') or payslip.contract_id and payslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('Deberías tener un contrato para crear una línea de recibo de nómina'))
        return super(ConsolidatedPayrollSlipLine, self).create(vals_list)
