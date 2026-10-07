# -*- coding: utf-8 -*-


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, api,fields
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round


class InventoryStockStatusReport(models.AbstractModel):
	_name = 'report.warehouse_report_app.report_stocklocationtransinfo' 
	_description = 'Inventory And Stock Location Transfer Report'

# Warehouse

	def _get_last_sale_details_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('warehouse_id', '=', warehouse_id),('picking_type_id.warehouse_id', '=', warehouse_id)]
		domain_quant += [('picking_type_id.code', '=', 'outgoing')]
		sale_order_line_ids =self.env['stock.move'].search(domain_quant, order="id desc", limit=1)
		return sale_order_line_ids

	def _get_last_purchase_details_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('warehouse_id', '=', warehouse_id),('picking_type_id.warehouse_id', '=', warehouse_id)]
		domain_quant += [('picking_type_id.code', '=', 'incoming')]
		purchase_order_line_ids =self.env['stock.move'].search(domain_quant, order="id desc", limit=1)
		return purchase_order_line_ids

	def _get_last_adjustment_details_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', 'in', ['done']), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += [('location_id.usage', '=', 'inventory')]
		adjusment_move_line_ids =self.env['stock.move'].search(domain_quant, order="id desc", limit=1)
		return adjusment_move_line_ids


	def _get_warehouse_details(self, data, warehouse):
		lines =[]
		if warehouse:
			start_date = data.get('start_date')
			end_date = data.get('end_date')
			category_ids = data.get('category_ids')
			filter_type = data.get('filter_type')
			product_ids = data.get('product_ids')
			company  = data.get('company_id')
			if filter_type == 'category':
				product_ids = self.env['product.product'].search([('categ_id', 'child_of', category_ids.ids)])
			else:
				product_ids = self.env['product.product'].search([('id', 'in', product_ids.ids)])
			product_data = []
			ending_stock = 0.0
			warehouse_id = warehouse.id
			company_id = company.id
			for product_id  in product_ids:
				value = {}
				counter = 1
				col = "col_"
				if product_id.product_template_attribute_value_ids:
					variant = product_id.product_template_attribute_value_ids._get_combination_name()
					name = variant and "%s (%s)" % (product_id.name, variant) or product_id.name
					product_name = name
				else:
					product_name = product_id.name

				price_used = product_id.standard_price

				last_sale_details = self._get_last_sale_details_info(product_id.id, warehouse_id, start_date, end_date, company_id)
				last_purchase_details = self._get_last_purchase_details_info(product_id.id, warehouse_id, start_date, end_date, company_id)
				last_adjustment_details = self._get_last_adjustment_details_info(product_id.id, warehouse_id, start_date, end_date, company_id)

				value.update({
					'product_id'			: product_id.id,
					'product_name'         	: product_name or '',
					'product_code'         	: product_id.default_code or '',
					'product_category'     	: product_id.categ_id.complete_name  or '',
					'sale_order_line'	   	: last_sale_details,
					'purchase_order_line'  	: last_purchase_details,
					'adjustment_line'  		: last_adjustment_details,
				})
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines

# Location

	def _get_last_location_sale_details_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('picking_type_id.code', '=', 'outgoing')]
		sale_order_line_ids =self.env['stock.move'].search(domain_quant, order="id desc", limit=1)
		return sale_order_line_ids

	def _get_last_location_purchase_details_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('picking_type_id.code', '=', 'incoming')]
		purchase_order_line_ids =self.env['stock.move'].search(domain_quant, order="id desc", limit=1)
		return purchase_order_line_ids

	def _get_last_location__adjustment_details_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', 'in', ['done']), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += [('location_id.usage', '=', 'inventory')]
		adjusment_move_line_ids =self.env['stock.move'].search(domain_quant, order="id desc", limit=1)
		return adjusment_move_line_ids

	def _get_location_details(self, data, location):
		lines =[]
		if location:
			start_date = data.get('start_date')
			end_date = data.get('end_date')
			category_ids = data.get('category_ids')
			filter_type = data.get('filter_type')
			product_ids = data.get('product_ids')
			company  = data.get('company_id')
			if filter_type == 'category':
				product_ids = self.env['product.product'].search([('categ_id', 'child_of', category_ids.ids)])
			else:
				product_ids = self.env['product.product'].search([('id', 'in', product_ids.ids)])
			product_data = []
			incoming_qty_total = 0.0
			outgoing_qty_total = 0.0
			internal_qty_total = 0.0
			inventory_qty_total = 0.0
			ending_stock = 0.0
			company_id = company.id
			for product_id  in product_ids:
				value = {}
				counter = 1
				col = "col_"
				if product_id.product_template_attribute_value_ids:
					variant = product_id.product_template_attribute_value_ids._get_combination_name()
					name = variant and "%s (%s)" % (product_id.name, variant) or product_id.name
					product_name = name
				else:
					product_name = product_id.name

				price_used = product_id.standard_price

				location_id = location.id

				last_sale_details = self._get_last_location_sale_details_info(product_id.id, location_id, start_date, end_date, company_id)
				last_purchase_details = self._get_last_location_purchase_details_info(product_id.id, location_id, start_date, end_date, company_id)
				last_adjustment_details = self._get_last_location__adjustment_details_info(product_id.id, location_id, start_date, end_date, company_id)


				value.update({
					'product_id'			: product_id.id,
					'product_name'         	: product_name or '',
					'product_code'         	: product_id.default_code or '',
					'product_category'     	: product_id.categ_id.complete_name  or '',
					'sale_order_line'	   	: last_sale_details,
					'purchase_order_line'  	: last_purchase_details,
					'adjustment_line'  		: last_adjustment_details,
				})
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines

	@api.model
	def _get_report_values(self, docids, data=None):
		company_id = self.env['res.company'].browse(data['form']['company_id'][0])
		start_date = data['form']['date_from']
		start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
		end_date = data['form']['date_to']
		end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y-%m-%d")
		filter_type = data['form']['filter_type']
		category_ids = self.env['product.category'].browse(data['form']['product_categ_ids'])
		product_ids  = self.env['product.product'].browse(data['form']['product_ids'])
		location_ids  = self.env['stock.location'].browse(data['form']['location_ids'])
		warehouse_ids = self.env['stock.warehouse'].browse(data['form']['warehouse_ids'])
		date_from = datetime.strptime(data['form']['date_from'], "%Y-%m-%d").strftime("%d-%m-%Y")
		date_to = datetime.strptime(data['form']['date_to'], "%Y-%m-%d").strftime("%d-%m-%Y")
		data  = { 
			'filter_type'   : filter_type,
			'start_date'    : start_date,
			'end_date'    	: end_date,
			'date_from'     : date_from,
			'date_to'     	: date_to,
			'warehouse_ids' : warehouse_ids,
			'location_ids'  : location_ids,
			'product_ids'	: product_ids,
			'category_ids'  : category_ids,
			'company_id'	: company_id
		} 
		docargs = {
				   'doc_model': 'stock.location.transfer.warehouse.report',
				   'data': data,
				   'get_warehouse_details':self._get_warehouse_details,
				   'get_location_details':self._get_location_details,
				   }
		return docargs