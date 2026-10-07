from odoo import fields, models


class PosPreparationDisplayOrderline(models.Model):
    _inherit = 'pos_preparation_display.orderline'

    pos_combo_list = fields.Text("Combo PoS")
