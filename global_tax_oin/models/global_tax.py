# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright 2025 Odoo IT now <http://www.odooitnow.com/>
# See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    tax_id = fields.Many2many('account.tax', 'sale_order_taxes',
                              string='Global Taxes')

    @api.onchange('tax_id')
    def onchange_order_tax(self):
        for order in self:
            for line in order.order_line:
                line.tax_id = [(6, 0, order.tax_id.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        sale_id = super(SaleOrder, self).create(vals_list)
        if sale_id.tax_id.ids:
            sale_id.onchange_order_tax()
        return sale_id

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for sale in self:
            if sale.tax_id.ids:
                sale.onchange_order_tax()
        return res


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    taxes_id = fields.Many2many('account.tax', 'purchase_order_taxes',
                                string='Global Taxes')

    @api.onchange('taxes_id')
    def onchange_order_tax(self):
        for order in self:
            for line in order.order_line:
                line.taxes_id = [(6, 0, order.taxes_id.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        purchase_id = super(PurchaseOrder, self).create(vals_list)
        if purchase_id.taxes_id.ids:
            purchase_id.onchange_order_tax()
        return purchase_id

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        for purchase in self:
            if purchase.taxes_id.ids:
                purchase.onchange_order_tax()
        return res
