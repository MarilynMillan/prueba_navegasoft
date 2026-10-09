from odoo import models, fields

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    rectified = fields.Boolean(
        string="Rectificación",
        help="¿El recibo de nómina es una rectificación?"
        #states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]}
        )