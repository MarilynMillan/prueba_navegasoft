from odoo import models, fields

class ConsolidatePayrollSlipAssoc(models.Model):
    _name = 'consolidated.payroll.slip.assoc'
    _description = 'Consolidado de nómina recibos asociados'

    slip_id = fields.Many2one('hr.payslip')
    consolidated_id = fields.Many2one('consolidated.payroll.slip')