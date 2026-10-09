
from odoo import api, Command, fields, models, _

class nomina_change(models.Model):
    _inherit = 'hr.salary.rule'

    sueldo_variable = fields.Boolean( 'Sueldo Variable', default=False)
    company_id=fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)

    
    