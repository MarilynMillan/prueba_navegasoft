from odoo import fields, models


class PosConfiguration(models.Model):
    _inherit = 'pos.config'

    custom_tip_percentage = fields.Float(string="Porcentaje",
                                         help="Ingrese el porcentaje de propinas personalizadas",
                                         )
