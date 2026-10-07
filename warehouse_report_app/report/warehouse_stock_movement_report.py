# -*- coding: utf-8 -*-


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, api,fields
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round


class InventoryStockMovementReport(models.AbstractModel):
	_name = 'report.warehouse_report_app.report_stockmovementsinfo' 
	_description = 'Inventory And Stock Movement Report'

# Warehouse

	def _get_stock_move_details_info(self, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('warehouse_id', '=', warehouse_id),('picking_type_id.warehouse_id', '=', warehouse_id)]
		stock_move_ids =self.env['stock.move'].search(domain_quant)
		return stock_move_ids


	def _get_warehouse_details(self, data, warehouse):
		lines =[]
		if warehouse:
			start_date = data.get('start_date')
			end_date = data.get('end_date')
			company  = data.get('company_id')
			product_data = []
			ending_stock = 0.0
			warehouse_id = warehouse.id
			company_id = company.id
			stock_move_details = self._get_stock_move_details_info(warehouse_id, start_date, end_date, company_id)
			product_data = []
			for move  in stock_move_details:
				value = {}
				if move.product_id.product_template_attribute_value_ids:
					variant = move.product_id.product_template_attribute_value_ids._get_combination_name()
					name = variant and "%s (%s)" % (move.product_id.name, variant) or move.product_id.name
					product_name = name
				else:
					product_name = move.product_id.name

				if move.picking_type_id.warehouse_id:
					picking_type_name = move.picking_type_id.warehouse_id.name + ': ' + move.picking_type_id.name
				else:
					picking_type_name = move.picking_type_id.name

				value.update({
					'move_id'				: move.id,
					'product_name'         	: product_name or '',
					'product_code'         	: move.product_id.default_code or '',
					'product_category'     	: move.product_id.categ_id.complete_name  or '',
					'inventory_date'		: move.date,
					'picking_type'			: picking_type_name,
					'source_location'		: move.location_id,
					'dest_location'			: move.location_dest_id,
					'product_uom_qty'		: move.product_uom_qty,
				})
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines

# Location

	def _get_stock_move_location_details_info(self, location_id, start_date, end_date, company_id):
		domain_quant = [('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		stock_move_ids =self.env['stock.move'].search(domain_quant)
		return stock_move_ids


	def _get_location_details(self, data, location):
		lines =[]
		if location:
			start_date = data.get('start_date')
			end_date = data.get('end_date')
			company  = data.get('company_id')
			product_data = []
			ending_stock = 0.0
			location_id = location.id
			company_id = company.id
			stock_move_details = self._get_stock_move_location_details_info(location_id, start_date, end_date, company_id)
			product_data = []
			for move  in stock_move_details:
				value = {}
				if move.product_id.product_template_attribute_value_ids:
					variant = move.product_id.product_template_attribute_value_ids._get_combination_name()
					name = variant and "%s (%s)" % (move.product_id.name, variant) or move.product_id.name
					product_name = name
				else:
					product_name = move.product_id.name

				if move.picking_type_id.warehouse_id:
					picking_type_name = move.picking_type_id.warehouse_id.name + ': ' + move.picking_type_id.name
				else:
					picking_type_name = move.picking_type_id.name

				value.update({
					'move_id'				: move.id,
					'product_name'         	: product_name or '',
					'product_code'         	: move.product_id.default_code or '',
					'product_category'     	: move.product_id.categ_id.complete_name  or '',
					'inventory_date'		: move.date,
					'picking_type'			: picking_type_name,
					'source_location'		: move.location_id,
					'dest_location'			: move.location_dest_id,
					'product_uom_qty'		: move.product_uom_qty,
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
		location_ids  = self.env['stock.location'].browse(data['form']['location_ids'])
		warehouse_ids = self.env['stock.warehouse'].browse(data['form']['warehouse_ids'])
		date_from = datetime.strptime(data['form']['date_from'], "%Y-%m-%d").strftime("%d-%m-%Y")
		date_to = datetime.strptime(data['form']['date_to'], "%Y-%m-%d").strftime("%d-%m-%Y")
		data  = { 
			'start_date'    : start_date,
			'end_date'    	: end_date,
			'date_from'     : date_from,
			'date_to'     	: date_to,
			'warehouse_ids' : warehouse_ids,
			'location_ids'  : location_ids,
			'company_id'	: company_id
		} 
		docargs = {
				   'doc_model': 'stock.movement.warehouse.report',
				   'data': data,
				   'get_warehouse_details':self._get_warehouse_details,
				   'get_location_details':self._get_location_details,
				   }
		return docargs