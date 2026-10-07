# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import json
from functools import partial
import ast
from itertools import groupby

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_combo_product = fields.Boolean(string=" Is Combo Product", help="Enables combo feature for this product.")
    hide_product_price = fields.Boolean(string="Hide Product Price", help="Enable to hide product price for this product.",default="False")
    pos_combo_groups_ids = fields.Many2many('combo.groups',string="Combo Groups",help="Select categories you want to add to this product.")
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        data = super()._load_pos_data_fields(config_id)
        data += ["is_combo_product", "hide_product_price", "pos_combo_groups_ids"]
        return data 
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ["is_combo_product", "hide_product_price", "pos_combo_groups_ids"]
        return params
    
class ComboGroups(models.Model):
    _name = 'combo.groups'

    name = fields.Char(string="Name")
    maximum_combo_products = fields.Integer("Maximum Combo Options",default=1 ,help="Maximum number of options that can be chosen from this category")
    minimum_combo_products = fields.Integer("Minimum Combo Options",default=0,help="Minimum number of options that can be chosen from this category.")
    combo_products_ids = fields.Many2many('combo.products',string="Category Options", help="Select options of your choice for this category.",required=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return []

    @api.model
    def _load_pos_data_domain(self, data):
        return []

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }
    
    @api.constrains('maximum_combo_products','minimum_combo_products','combo_products_ids')
    def validate_min_max_combo_products(self):
        """
        Raises validation errors based on necessary condition
        """
        if self.maximum_combo_products < 0 or self.minimum_combo_products < 0:
            raise ValidationError("Number of combo products cannot be negative.")
        if self.minimum_combo_products > self.maximum_combo_products:
            raise ValidationError("Minimum value cannot be greater than maximum value for combo products.")
       
class ComboProducts(models.Model):
    
    _name = 'combo.products'

    name = fields.Char(string="Name",required=True)
    image = fields.Binary(string="Image")
    price = fields.Float(string="Price")
    manage_inventory = fields.Boolean(string="Manage Inventory",default=False)
    product_id = fields.Many2one('product.product' , string="Products")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return []

    @api.model
    def _load_pos_data_domain(self, data):
        return []

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }

class PosConfig(models.Model):
    _inherit = 'pos.config'

    combo_popup_view = fields.Selection(
        [('grid', 'Grid View'), ('list', 'List View')],
        'Status',required=True,readonly=True, copy=False, default='grid')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_combo_popup_view = fields.Selection(related='pos_config_id.combo_popup_view',readonly=False)

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['combo.products', 'combo.groups']
        return data


class StockPicking(models.Model):
    _inherit='stock.picking'

    def _prepare_stock_move_combo_vals(self, line, qty,product):
        """
        Params:
        line:line of combo product
        qty:int qty of product selected in combo product
        product:product selected in combo product 
        returns combo product data for picking
        """
        result = {
            'name': line.name,
            'product_uom': line.product_id.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id':product.id,
            'product_uom_qty': qty,
            'state': 'draft',
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }
        return result

    def _create_move_from_pos_order_lines(self, lines):
        """
        core function override to create picking for lines in combo product
        """
        self.ensure_one()
        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
        move_vals = []
        for dummy, olines in lines_by_product:
            order_lines = self.env['pos.order.line'].concat(*olines)
            move_vals.append(self._prepare_stock_move_vals(order_lines[0], order_lines))

        # picking code for combo products
        combo_lines = lines.filtered(lambda l: l.product_id.pos_combo_groups_ids and l.product_id.is_combo_product and l.qty_combo_dict)
        for line in combo_lines:
            cached_json = ast.literal_eval(line.qty_combo_dict)
            if line.product_id.pos_combo_groups_ids:
                for key,value in cached_json.items():
                    if key and value:         
                        inventory_product = self.env['product.product'].browse(int(key)) 
                        if inventory_product and inventory_product.type in ['product', 'consu']:
                            move_vals.append(self._prepare_stock_move_combo_vals(line,value,inventory_product ))
                        
        #code end
        moves = self.env['stock.move'].create(move_vals)
        confirmed_moves = moves._action_confirm()
        confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)

    
class PosOrder(models.Model):
    _inherit = 'pos.order'

    qty_combo_dict = fields.Text()
    qty_wk_combo_ids  = fields.Text("Products")
    qty_combo_list_name = fields.Text()
    
    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.extend([
            'sel_combo_prod','qty_combo_dict','temp_arr','grid_temp_arr','is_combo_product'
        ])
        return fields
    

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_combo_product = fields.Boolean("Combo Product")
    qty_combo_dict = fields.Text()
    sel_combo_prod = fields.Text()
    temp_arr = fields.Text()
    grid_temp_arr = fields.Text()
    grid_template_dict = fields.Text()
    template_dict = fields.Text()

    def _load_pos_data_fields(self, config_id):
        data = super()._load_pos_data_fields(config_id)
        data += ["is_combo_product", "qty_combo_dict", "sel_combo_prod", "temp_arr", "grid_temp_arr", "grid_template_dict", "template_dict"]
        return data 

    
