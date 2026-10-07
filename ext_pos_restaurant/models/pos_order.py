from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    initial_customer_count = fields.Boolean(string='Initial Customer Count', default=False)