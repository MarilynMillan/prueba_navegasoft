# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = "pos.config"

    enable_pos_restaurant_restiction = fields.Boolean("Restaurant Restriction", default=True)
    enable_restriction_on_orderline_delete = fields.Boolean("Enable Restriction on Orderline Delete", default=True)
    enable_restriction_on_order_delete = fields.Boolean("Enable Restriction on Order Delete", default=True)
    enable_restriction_on_session_close = fields.Boolean("Enable Restriction on Session Close", default=True)
    enable_qty_update = fields.Boolean("Enable Restriction on Orderline Quantity Update", default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_pos_restaurant_restiction = fields.Boolean(related="pos_config_id.enable_pos_restaurant_restiction", readonly=False)
    is_restriction_on_orderline_delete = fields.Boolean(related="pos_config_id.enable_restriction_on_orderline_delete", readonly=False)
    is_restriction_on_order_delete = fields.Boolean(related="pos_config_id.enable_restriction_on_order_delete", readonly=False)
    is_restriction_on_session_close = fields.Boolean(related="pos_config_id.enable_restriction_on_session_close", readonly=False)
    is_restriction_on_orderline_qty_update = fields.Boolean(related="pos_config_id.enable_qty_update", readonly=False)
