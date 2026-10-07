# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_auto_invoice = fields.Boolean('Auto Invoicing')
    block_auto_invoice = fields.Boolean('Block Invoicing')

    @api.onchange('is_auto_invoice')
    def onchange_is_auto_invoice(self):
        for record in self:
            if not record.is_auto_invoice:
                record.block_auto_invoice = False

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_auto_invoice = fields.Boolean(related='pos_config_id.is_auto_invoice',readonly=False)
    block_auto_invoice = fields.Boolean(related='pos_config_id.block_auto_invoice',readonly=False)

    @api.onchange('is_auto_invoice')
    def onchange_is_auto_invoice(self):
        for record in self:
            if not record.is_auto_invoice:
                record.block_auto_invoice = False