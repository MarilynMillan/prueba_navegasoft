# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    ds_adjustment_record_id = fields.Many2one(
        'ds.inventory.adjustment',
        string='Ajuste Retroactivo',
        index=True,
        copy=False,
    )
