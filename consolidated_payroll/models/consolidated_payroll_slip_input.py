from odoo import fields, models


class ConsolidatedPayrollSlipInput(models.Model):
    _name = 'consolidated.payroll.slip.input'
    _description = 'Otras entradas recibo de nómina'
    _order = 'payslip_id, sequence'

    name = fields.Char(string="Descripción", readonly=True)
    payslip_id = fields.Many2one('consolidated.payroll.slip', string='Pay Slip', required=True,  index=True, readonly=True)#ondelete='cascade',
    sequence = fields.Integer(required=True, index=True, default=10)
    input_type_id = fields.Many2one('hr.payslip.input.type', string='Tipo', required=True, readonly=True)
    code = fields.Char(related='input_type_id.code', required=True, readonly=True)
    amount = fields.Float(string="Cuenta", readonly=True)
    contract_id = fields.Many2one(related='payslip_id.contract_id', string='Contrato', required=True, readonly=True)
