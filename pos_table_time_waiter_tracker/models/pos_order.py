# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    start_time = fields.Datetime('Start Time')
    end_time = fields.Datetime('End Time')
    duration = fields.Float('Duration')
    waiter_name = fields.Char('Waiter Name')  # Add this line


class PosConfig(models.Model):
    _inherit = 'pos.config'

    table_timer_enable = fields.Boolean()
    table_waiter_name_enable = fields.Boolean()
    table_order_amount_enable = fields.Boolean()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_table_timer_enable = fields.Boolean(
        related='pos_config_id.table_timer_enable', readonly=False
    )
    pos_table_waiter_name_enable = fields.Boolean(
        related='pos_config_id.table_waiter_name_enable', readonly=False
    )
    pos_table_order_amount_enable = fields.Boolean(
        related='pos_config_id.table_order_amount_enable', readonly=False
    )
