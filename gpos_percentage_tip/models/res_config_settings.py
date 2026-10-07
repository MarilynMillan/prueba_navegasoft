from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_custom_tip_percentage = fields.Float(string="Porcentaje",
                                         help="Ingrese el porcentaje de propinas personalizadas",
                                         related = "pos_config_id.custom_tip_percentage")
