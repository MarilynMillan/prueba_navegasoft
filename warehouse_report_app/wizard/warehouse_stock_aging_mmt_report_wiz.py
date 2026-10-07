# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round

import logging
_logger = logging.getLogger(__name__)

try:
	import xlsxwriter
except ImportError:
	_logger.debug('Cannot `import xlsxwriter`.')
try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')

class StockAgingWarehouseMovementReport(models.TransientModel):
	_name = 'stock.aging.warehouse.movement.report'
	_description = 'Stock Aging Movement Report'
	
	date_from = fields.Date('Start Date')
	warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
	location_ids = fields.Many2many('stock.location', string="Location")
	product_ids = fields.Many2many('product.product', string="Product")
	product_categ_ids = fields.Many2many('product.category', string="Category")
	filter_type = fields.Selection([('product','Product'),('category','Category')], default='product', string='Filter By')
	document = fields.Binary('File To Download')
	file = fields.Char('Report File Name', readonly=1)
	period_length = fields.Integer('Period Length (Days)', default=30)
	company_id = fields.Many2one('res.company','Company')
	report_type = fields.Selection([('warehouse','Warehouse'),('location','Location')], default='warehouse', string='Generate Report Based on')

	@api.onchange('filter_type')
	def _onchange_filter_type(self):
		if self.filter_type == 'product':
			self.product_categ_ids = False
		else:
			self.product_ids = False

	@api.onchange('report_type')
	def _onchange_report_type(self):
		if self.report_type == 'warehouse':
			self.location_ids = False
		else:
			self.warehouse_ids = False

	def print_pdf_report(self):
		self.ensure_one()
		[data] = self.read()
		datas = {
			 'ids': [1],
			 'model': 'stock.aging.warehouse.movement.report',
			 'form': data
		}
		return self.env.ref('warehouse_report_app.action_stock_aging_ware_movement').report_action(self, data=datas)

	def get_columns(self, data):
		period_length = data.get('period_length')
		column_data = []
		current_period_lenth = 0
		for i in range(0,4):
			col = str(current_period_lenth) + "-" + str(current_period_lenth + period_length)
			current_period_lenth += period_length
			column_data.append(col)
		col = "> " + str(current_period_lenth)
		column_data.append(col)
		return column_data

	def _get_date_data(self, datas):
		start_date = False
		end_date = False
		date_data = []
		for i in range(0, 5):
			data = {}
			if i <= 0:
				start_date = datas.get('start_date')
				end_date = (datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)) + timedelta(days= datas.get('period_length'))
				if isinstance(start_date, datetime):
					start_date = datetime.strftime(start_date, DEFAULT_SERVER_DATE_FORMAT)
				if isinstance(end_date, datetime):
					end_date = datetime.strftime(end_date, DEFAULT_SERVER_DATE_FORMAT)
				data.update({'start_date':start_date,'end_date':end_date})
				date_data.append(data)
				start_date = (datetime.strptime(datas.get('start_date'), DEFAULT_SERVER_DATE_FORMAT))
			else:
				start_date = start_date + timedelta(days= datas.get('period_length'))
				end_date = end_date + timedelta(days= datas.get('period_length'))
				if isinstance(start_date, datetime):
					start_date = datetime.strftime(start_date, DEFAULT_SERVER_DATE_FORMAT)
				if isinstance(end_date, datetime):
					end_date = datetime.strftime(end_date, DEFAULT_SERVER_DATE_FORMAT)
				data.update({'start_date':start_date,'end_date':end_date})
				date_data.append(data)
			if isinstance(start_date, str):
				start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
			if isinstance(end_date, str):
				end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
		return date_data

# Warehouse


	def _get_product_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_product_in_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_return_in_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('location_id.usage', '=', 'internal'),('location_dest_id.usage', '=', 'internal')]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_return_out_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('location_id.usage', '=', 'internal'),('location_dest_id.usage', '=', 'internal')]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_adjusted_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('location_id.usage', '=', 'inventory')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def get_warehouse_details(self, data, warehouse):
		lines =[]
		if warehouse:
			start_date_data = data.get('start_date')
			category_ids = data.get('category_ids')
			filter_type = data.get('filter_type')
			product_ids = data.get('product_ids')
			company  = data.get('company_id')
			if filter_type == 'category':
				product_ids = self.env['product.product'].search([('categ_id', 'in', category_ids.ids)])
			else:
				product_ids = self.env['product.product'].search([('id', 'in', product_ids.ids)])
			product_data = []
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
				value.update({
					'product_id'         : product_id.id,
					'product_name'       : product_name or '',
					'product_code'       : product_id.default_code or '',
					'cost_price'         : product_id.standard_price  or 0.00,
				})
				is_last = False
				for date_data in self._get_date_data(data):
					if counter == 6:
						is_last = True
					start_date = date_data.get('start_date')
					end_date = date_data.get('end_date')
					warehouse_id = warehouse.id
					company_id = company.id
					delivered_qty = self._get_product_info(product_id.id, warehouse_id, start_date, end_date, company_id)
					received_qty = self._get_product_in_info(product_id.id, warehouse_id, start_date, end_date, company_id)
					return_in_qty = self._get_return_in_qty(product_id.id, warehouse_id, start_date, end_date, company_id)
					return_out_qty = self._get_return_out_qty(product_id.id, warehouse_id, start_date, end_date, company_id)
					adjusted_qty = self._get_adjusted_qty(product_id.id, warehouse_id, start_date, end_date, company_id)
					
					adjusted_qty_on_hand = adjusted_qty
					received_qty_on_hand = received_qty + return_in_qty
					delivered_qty_on_hand = delivered_qty + return_out_qty

					# qty_on_hand = (received_qty + adjusted_qty + return_in_qty) - (delivered_qty - return_out_qty)
					adjusted_qty_hand_key = col + 'adjustment' + str(counter)
					received_qty_hand_key = col + 'received' + str(counter)
					delivered_qty_hand_key = col + 'delivered' + str(counter)

					value.update({
						adjusted_qty_hand_key : adjusted_qty_on_hand,
						received_qty_hand_key : received_qty_on_hand,
						delivered_qty_hand_key : delivered_qty_on_hand,
					})
					counter += 1
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines


# Location

	def _get_product_location_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_product_location_in_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_return_location_in_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing')]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_return_location_out_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming')]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_adjusted_location_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('location_id.usage', '=', 'inventory')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def get_location_details(self, data, location):
		lines =[]
		if location:
			start_date_data = data.get('start_date')
			category_ids = data.get('category_ids')
			filter_type = data.get('filter_type')
			product_ids = data.get('product_ids')
			company  = data.get('company_id')
			if filter_type == 'category':
				product_ids = self.env['product.product'].search([('categ_id', 'in', category_ids.ids)])
			else:
				product_ids = self.env['product.product'].search([('id', 'in', product_ids.ids)])
			product_data = []
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
				value.update({
					'product_id'         : product_id.id,
					'product_name'       : product_name or '',
					'product_code'       : product_id.default_code or '',
					'cost_price'         : product_id.standard_price  or 0.00,
				})
				is_last = False
				for date_data in self._get_date_data(data):
					if counter == 6:
						is_last = True
					start_date = date_data.get('start_date')
					end_date = date_data.get('end_date')
					company_id = company.id
					location_id = location.id
					delivered_qty = self._get_product_location_info(product_id.id, location_id, start_date, end_date, company_id)
					received_qty = self._get_product_location_in_info(product_id.id, location_id, start_date, end_date, company_id)
					return_in_qty = self._get_return_location_in_qty(product_id.id, location_id, start_date, end_date, company_id)
					return_out_qty = self._get_return_location_out_qty(product_id.id, location_id, start_date, end_date, company_id)
					adjusted_qty = self._get_adjusted_location_qty(product_id.id, location_id, start_date, end_date, company_id)

					adjusted_qty_on_hand = adjusted_qty
					received_qty_on_hand = received_qty + return_in_qty
					delivered_qty_on_hand = delivered_qty + return_out_qty

					# qty_on_hand = (received_qty + adjusted_qty + return_in_qty) - (delivered_qty - return_out_qty)
					adjusted_qty_hand_key = col + 'adjustment' + str(counter)
					received_qty_hand_key = col + 'received' + str(counter)
					delivered_qty_hand_key = col + 'delivered' + str(counter)

					value.update({
						adjusted_qty_hand_key : adjusted_qty_on_hand,
						received_qty_hand_key : received_qty_on_hand,
						delivered_qty_hand_key : delivered_qty_on_hand,
					})
					counter += 1
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines



	def print_excel_report(self):
		self.ensure_one()
		[data] = self.read()
		file_path = 'Stock Aging Movement Report' + '.xlsx'
		workbook = xlsxwriter.Workbook('/tmp/' + file_path)
		worksheet = workbook.add_worksheet('Stock Aging Movement Report')

		header_format = workbook.add_format({'bold': True,'valign':'vcenter','font_size':16,'align': 'center','bg_color':'#D8D8D8'})
		title_format = workbook.add_format({'border': 1,'bold': True, 'valign': 'vcenter','align': 'center', 'font_size':14,'bg_color':'#D8D8D8'})
		cell_wrap_format = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'left','font_size':12,}) ##E6E6E6
		cell_wrap_format_right = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,}) ##E6E6E6
		cell_wrap_format_val = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,}) ##E6E6E6
		cell_wrap_format_val.set_font_color('#006600')
		cell_wrap_format_bold = workbook.add_format({'border': 1, 'bold': True,'valign':'vjustify','valign':'vcenter','align': 'center','font_size':12,'bg_color':'#D8D8D8'}) ##E6E6E6
		cell_wrap_format_amount = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bold': True}) ##E6E6E6
		cell_wrap_format_amount_val = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bold': True}) ##E6E6E6
		cell_wrap_format_amount.set_font_color('#006600')

		worksheet.set_row(1,20)  #Set row height
		#Merge Row Columns
		TITLEHEDER = 'Stock Aging Movement Report' 
		worksheet.set_column(0, 0, 15)
		worksheet.set_column(1, 1, 25)
		worksheet.set_column(2, 31, 15)

		ware_obj = self.env['stock.warehouse']
		location_obj = self.env['stock.location']

		period_length = data.get('period_length')
		start_date = data.get('date_from')
		start_date = datetime.strptime(str(start_date), "%Y-%m-%d").strftime("%Y-%m-%d")
		filter_type = data.get('filter_type')
		category_ids = self.env['product.category'].browse(data.get('product_categ_ids'))
		product_ids  = self.env['product.product'].browse(data.get('product_ids'))
		location_ids  = self.env['stock.location'].browse(data.get('location_ids'))
		warehouse_ids = self.env['stock.warehouse'].browse(data.get('warehouse_ids'))
		date_from = datetime.strptime(str(data.get('date_from')), "%Y-%m-%d").strftime("%d-%m-%Y")
		company_id = self.env['res.company'].browse(data.get('company_id')[0])
		data  = { 
			'filter_type'   : filter_type,
			'start_date'    : start_date,
			'date_from'     : date_from,
			'warehouse_ids' : warehouse_ids,
			'location_ids'  : location_ids,
			'product_ids'	: product_ids,
			'category_ids'  : category_ids,
			'period_length' : period_length,
			'company_id'	: company_id
		}

		worksheet.merge_range(1, 0, 1, 31, TITLEHEDER,header_format)
		rowscol = 1
		if warehouse_ids:
			for warehouse in warehouse_ids:
				# Report Title
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 5,'Warehouse/Location', title_format)
				worksheet.merge_range((rowscol + 2), 26, (rowscol + 2), 31, str(warehouse.name) , title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 5,'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 5, str(company_id.name) , title_format)

				worksheet.merge_range((rowscol + 4), 10, (rowscol + 4), 15,'Start Date: ', title_format)
				worksheet.merge_range((rowscol + 5), 10, (rowscol + 5), 15, str(start_date) , title_format)

				worksheet.merge_range((rowscol + 4), 26, (rowscol + 4), 31,'Period Length:', title_format)
				worksheet.merge_range((rowscol + 5), 26, (rowscol + 5), 31, str(period_length) , title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				col = 2
				for value in self.get_columns(data):
					colss = col + 5
					worksheet.merge_range((rowscol + 7), col, (rowscol + 7), colss, str(value), title_format)
					col += 6

				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 2, (rowscol + 8), 3, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 4, (rowscol + 8), 5, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 6, (rowscol + 8), 7, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 8, (rowscol + 8), 9, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 10, (rowscol + 8), 11, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 12, (rowscol + 8), 13, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 14, (rowscol + 8), 15, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 16, (rowscol + 8), 17, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 18, (rowscol + 8), 19, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 20, (rowscol + 8), 21, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 22, (rowscol + 8), 23, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 24, (rowscol + 8), 25, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 26, (rowscol + 8), 27, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 28, (rowscol + 8), 29, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 30, (rowscol + 8), 31, 'Adjust', cell_wrap_format_bold)

				
				worksheet.write((rowscol + 9), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 2, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 3, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 4, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 5, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 6, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 7, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 8, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 9, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 10, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 11, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 12, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 13, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 14, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 15, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 16, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 17, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 18, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 19, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 20, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 21, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 22, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 23, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 24, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 25, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 26, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 27, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 28, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 29, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 30, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 31, 'Value', cell_wrap_format_bold)
				rows = (rowscol + 10)
				for records in self.get_warehouse_details(data, warehouse):
					for record in records.get('product_data'):
						col_received1_data = record.get('col_received1')
						col_delivered1_data = record.get('col_delivered1')
						col_adjustment1_data = record.get('col_adjustment1')

						col_received2_data = record.get('col_received2')
						col_delivered2_data = record.get('col_delivered2')
						col_adjustment2_data = record.get('col_adjustment2')

						col_received3_data = record.get('col_received3')
						col_delivered3_data = record.get('col_delivered3')
						col_adjustment3_data = record.get('col_adjustment3')

						col_received4_data = record.get('col_received4')
						col_delivered4_data = record.get('col_delivered4')
						col_adjustment4_data = record.get('col_adjustment4')

						col_received5_data = record.get('col_received5')
						col_delivered5_data = record.get('col_delivered5')
						col_adjustment5_data = record.get('col_adjustment5')
						

						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)

						worksheet.write(rows, 2,  str('%.1f' % col_delivered1_data), cell_wrap_format_amount)
						col_delivered1_data_value = col_delivered1_data * record.get('cost_price')
						worksheet.write(rows, 3,  str('%.2f' % col_delivered1_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 4,  str('%.1f' % col_received1_data), cell_wrap_format_amount)
						col_received1_data_value = col_received1_data * record.get('cost_price')
						worksheet.write(rows, 5,  str('%.2f' % col_received1_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 6,  str('%.1f' % col_adjustment1_data), cell_wrap_format_amount)
						col_adjustment1_data_value = col_adjustment1_data * record.get('cost_price')
						worksheet.write(rows, 7,  str('%.2f' % col_adjustment1_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 8,  str('%.1f' % col_delivered2_data), cell_wrap_format_amount)
						col_delivered2_data_value = col_delivered2_data * record.get('cost_price')
						worksheet.write(rows, 9,  str('%.2f' % col_delivered2_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 10,  str('%.1f' % col_received2_data), cell_wrap_format_amount)
						col_received2_data_value = col_received2_data * record.get('cost_price')
						worksheet.write(rows, 11,  str('%.2f' % col_received2_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 12,  str('%.1f' % col_adjustment2_data), cell_wrap_format_amount)
						col_adjustment2_data_value = col_adjustment2_data * record.get('cost_price')
						worksheet.write(rows, 13,  str('%.2f' % col_adjustment2_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 14,  str('%.1f' % col_delivered3_data), cell_wrap_format_amount)
						col_delivered3_data_value = col_delivered3_data * record.get('cost_price')
						worksheet.write(rows, 15,  str('%.2f' % col_delivered3_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 16,  str('%.1f' % col_received3_data), cell_wrap_format_amount)
						col_received3_data_value = col_received3_data * record.get('cost_price')
						worksheet.write(rows, 17,  str('%.2f' % col_received3_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 18,  str('%.1f' % col_adjustment3_data), cell_wrap_format_amount)
						col_adjustment3_data_value = col_adjustment3_data * record.get('cost_price')
						worksheet.write(rows, 19,  str('%.2f' % col_adjustment3_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 20,  str('%.1f' % col_delivered4_data), cell_wrap_format_amount)
						col_delivered4_data_value = col_delivered4_data * record.get('cost_price')
						worksheet.write(rows, 21,  str('%.2f' % col_delivered4_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 22,  str('%.1f' % col_received4_data), cell_wrap_format_amount)
						col_received4_data_value = col_received4_data * record.get('cost_price')
						worksheet.write(rows, 23,  str('%.2f' % col_received4_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 24,  str('%.1f' % col_adjustment4_data), cell_wrap_format_amount)
						col_adjustment4_data_value = col_adjustment4_data * record.get('cost_price')
						worksheet.write(rows, 25,  str('%.2f' % col_adjustment4_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 26,  str('%.1f' % col_delivered5_data), cell_wrap_format_amount)
						col_delivered5_data_value = col_delivered5_data * record.get('cost_price')
						worksheet.write(rows, 27,  str('%.2f' % col_delivered5_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 28,  str('%.1f' % col_received5_data), cell_wrap_format_amount)
						col_received5_data_value = col_received5_data * record.get('cost_price')
						worksheet.write(rows, 29,  str('%.2f' % col_received5_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 30,  str('%.1f' % col_adjustment5_data), cell_wrap_format_amount)
						col_adjustment5_data_value = col_adjustment5_data * record.get('cost_price')
						worksheet.write(rows, 31,  str('%.2f' % col_adjustment5_data_value), cell_wrap_format_amount_val)
						rows = rows + 1
					rows = rows
				rowscol = rows + 2
		else:
			for location in location_ids:
				if location.location_id:
					location_name = str(location.location_id.name or '') + '/' + str(location.name or '') 
				else:
					location_name = str(location.name or '') 
				# Report Title
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 5,'Warehouse/Location', title_format)
				worksheet.merge_range((rowscol + 2), 26, (rowscol + 2), 31, str(location_name) , title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 5,'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 5, str(company_id.name) , title_format)

				worksheet.merge_range((rowscol + 4), 10, (rowscol + 4), 15,'Start Date: ', title_format)
				worksheet.merge_range((rowscol + 5), 10, (rowscol + 5), 15, str(start_date) , title_format)

				worksheet.merge_range((rowscol + 4), 26, (rowscol + 4), 31,'Period Length:', title_format)
				worksheet.merge_range((rowscol + 5), 26, (rowscol + 5), 31, str(period_length) , title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				col = 2
				for value in self.get_columns(data):
					colss = col + 5
					worksheet.merge_range((rowscol + 7), col, (rowscol + 7), colss, str(value), title_format)
					col += 6

				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 2, (rowscol + 8), 3, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 4, (rowscol + 8), 5, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 6, (rowscol + 8), 7, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 8, (rowscol + 8), 9, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 10, (rowscol + 8), 11, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 12, (rowscol + 8), 13, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 14, (rowscol + 8), 15, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 16, (rowscol + 8), 17, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 18, (rowscol + 8), 19, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 20, (rowscol + 8), 21, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 22, (rowscol + 8), 23, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 24, (rowscol + 8), 25, 'Adjust', cell_wrap_format_bold)

				worksheet.merge_range((rowscol + 8), 26, (rowscol + 8), 27, 'Sale', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 28, (rowscol + 8), 29, 'Purchase', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 8), 30, (rowscol + 8), 31, 'Adjust', cell_wrap_format_bold)

				
				worksheet.write((rowscol + 9), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 2, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 3, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 4, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 5, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 6, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 7, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 8, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 9, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 10, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 11, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 12, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 13, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 14, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 15, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 16, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 17, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 18, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 19, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 20, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 21, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 22, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 23, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 24, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 25, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 26, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 27, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 28, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 29, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 30, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 9), 31, 'Value', cell_wrap_format_bold)
				rows = (rowscol + 10)
				for records in self.get_location_details(data, location):
					for record in records.get('product_data'):
						col_received1_data = record.get('col_received1')
						col_delivered1_data = record.get('col_delivered1')
						col_adjustment1_data = record.get('col_adjustment1')

						col_received2_data = record.get('col_received2')
						col_delivered2_data = record.get('col_delivered2')
						col_adjustment2_data = record.get('col_adjustment2')

						col_received3_data = record.get('col_received3')
						col_delivered3_data = record.get('col_delivered3')
						col_adjustment3_data = record.get('col_adjustment3')

						col_received4_data = record.get('col_received4')
						col_delivered4_data = record.get('col_delivered4')
						col_adjustment4_data = record.get('col_adjustment4')

						col_received5_data = record.get('col_received5')
						col_delivered5_data = record.get('col_delivered5')
						col_adjustment5_data = record.get('col_adjustment5')
						

						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)

						worksheet.write(rows, 2,  str('%.1f' % col_delivered1_data), cell_wrap_format_amount)
						col_delivered1_data_value = col_delivered1_data * record.get('cost_price')
						worksheet.write(rows, 3,  str('%.2f' % col_delivered1_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 4,  str('%.1f' % col_received1_data), cell_wrap_format_amount)
						col_received1_data_value = col_received1_data * record.get('cost_price')
						worksheet.write(rows, 5,  str('%.2f' % col_received1_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 6,  str('%.1f' % col_adjustment1_data), cell_wrap_format_amount)
						col_adjustment1_data_value = col_adjustment1_data * record.get('cost_price')
						worksheet.write(rows, 7,  str('%.2f' % col_adjustment1_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 8,  str('%.1f' % col_delivered2_data), cell_wrap_format_amount)
						col_delivered2_data_value = col_delivered2_data * record.get('cost_price')
						worksheet.write(rows, 9,  str('%.2f' % col_delivered2_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 10,  str('%.1f' % col_received2_data), cell_wrap_format_amount)
						col_received2_data_value = col_received2_data * record.get('cost_price')
						worksheet.write(rows, 11,  str('%.2f' % col_received2_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 12,  str('%.1f' % col_adjustment2_data), cell_wrap_format_amount)
						col_adjustment2_data_value = col_adjustment2_data * record.get('cost_price')
						worksheet.write(rows, 13,  str('%.2f' % col_adjustment2_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 14,  str('%.1f' % col_delivered3_data), cell_wrap_format_amount)
						col_delivered3_data_value = col_delivered3_data * record.get('cost_price')
						worksheet.write(rows, 15,  str('%.2f' % col_delivered3_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 16,  str('%.1f' % col_received3_data), cell_wrap_format_amount)
						col_received3_data_value = col_received3_data * record.get('cost_price')
						worksheet.write(rows, 17,  str('%.2f' % col_received3_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 18,  str('%.1f' % col_adjustment3_data), cell_wrap_format_amount)
						col_adjustment3_data_value = col_adjustment3_data * record.get('cost_price')
						worksheet.write(rows, 19,  str('%.2f' % col_adjustment3_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 20,  str('%.1f' % col_delivered4_data), cell_wrap_format_amount)
						col_delivered4_data_value = col_delivered4_data * record.get('cost_price')
						worksheet.write(rows, 21,  str('%.2f' % col_delivered4_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 22,  str('%.1f' % col_received4_data), cell_wrap_format_amount)
						col_received4_data_value = col_received4_data * record.get('cost_price')
						worksheet.write(rows, 23,  str('%.2f' % col_received4_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 24,  str('%.1f' % col_adjustment4_data), cell_wrap_format_amount)
						col_adjustment4_data_value = col_adjustment4_data * record.get('cost_price')
						worksheet.write(rows, 25,  str('%.2f' % col_adjustment4_data_value), cell_wrap_format_amount_val)

						worksheet.write(rows, 26,  str('%.1f' % col_delivered5_data), cell_wrap_format_amount)
						col_delivered5_data_value = col_delivered5_data * record.get('cost_price')
						worksheet.write(rows, 27,  str('%.2f' % col_delivered5_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 28,  str('%.1f' % col_received5_data), cell_wrap_format_amount)
						col_received5_data_value = col_received5_data * record.get('cost_price')
						worksheet.write(rows, 29,  str('%.2f' % col_received5_data_value), cell_wrap_format_amount_val)
						worksheet.write(rows, 30,  str('%.1f' % col_adjustment5_data), cell_wrap_format_amount)
						col_adjustment5_data_value = col_adjustment5_data * record.get('cost_price')
						worksheet.write(rows, 31,  str('%.2f' % col_adjustment5_data_value), cell_wrap_format_amount_val)
						rows = rows + 1
					rows = rows
				rowscol = rows + 2
		workbook.close()
		buf = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())
		self.document = buf
		self.file = 'Stock Aging Movement Report'+'.xlsx'
		return {
			'res_id': self.id,
			'name': 'Files to Download',
			'view_type': 'form',
			"view_mode": 'form,list',
			'res_model': 'stock.aging.warehouse.movement.report',
			'type': 'ir.actions.act_window',
			'target': 'new',
		}