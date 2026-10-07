# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
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

class StockLocationTransferReport(models.TransientModel):
	_name = 'stock.location.transfer.warehouse.report'
	_description = 'Inventory And Stock Location Transfer Report'

	date_from = fields.Date('Start Date')
	date_to = fields.Date('End Date')
	warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
	location_ids = fields.Many2many('stock.location', string="Location")
	product_ids = fields.Many2many('product.product', string="Product")
	product_categ_ids = fields.Many2many('product.category', string="Category")
	filter_type = fields.Selection([('product','Product'),('category','Category')], default='product', string='Filter By')
	document = fields.Binary('File To Download')
	file = fields.Char('Report File Name', readonly=1)
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
			 'model': 'stock.location.transfer.warehouse.report',
			 'form': data
		}
		return self.env.ref('warehouse_report_app.action_report_stock_location_trans').report_action(self, data=datas)


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


	def get_warehouse_details(self, data, warehouse):
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

	def get_location_details(self, data, location):
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


	def print_excel_report(self):
		self.ensure_one()
		[data] = self.read()
		file_path = 'Inventory And Stock Location Transfer Report' + '.xlsx'
		workbook = xlsxwriter.Workbook('/tmp/' + file_path)
		worksheet = workbook.add_worksheet('Inventory And Stock Location Transfer Report')

		header_format = workbook.add_format({'bold': True,'valign':'vcenter','font_size':16,'align': 'center','bg_color':'#D8D8D8'})
		title_format = workbook.add_format({'border': 1,'bold': True, 'valign': 'vcenter','align': 'center', 'font_size':14,'bg_color':'#D8D8D8'})
		cell_wrap_format = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'left','font_size':12,}) ##E6E6E6
		cell_wrap_format_right = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,}) ##E6E6E6
		cell_wrap_format_val = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,}) ##E6E6E6
		cell_wrap_format_val.set_font_color('#006600')
		cell_wrap_format_bold = workbook.add_format({'border': 1, 'bold': True,'valign':'vjustify','valign':'vcenter','align': 'center','font_size':12,'bg_color':'#D8D8D8'}) ##E6E6E6
		cell_wrap_format_amount_val = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bold': True}) ##E6E6E6

		worksheet.set_row(1,20)  #Set row height
		#Merge Row Columns
		TITLEHEDER = 'Inventory And Stock Location Transfer Report' 
		worksheet.set_column(0, 1, 40)
		worksheet.set_column(2, 7, 30)
		worksheet.set_column(8, 8, 45)
		worksheet.set_column(9, 14, 30)

		ware_obj = self.env['stock.warehouse']
		location_obj = self.env['stock.location']

		start_date = datetime.strptime(str(data.get('date_from')), "%Y-%m-%d").strftime("%Y-%m-%d")
		end_date = datetime.strptime(str(data.get('date_to')), "%Y-%m-%d").strftime("%Y-%m-%d")

		filter_type = data.get('filter_type')
		category_ids = self.env['product.category'].browse(data.get('product_categ_ids'))
		product_ids  = self.env['product.product'].browse(data.get('product_ids'))
		location_ids  = self.env['stock.location'].browse(data.get('location_ids'))
		warehouse_ids = self.env['stock.warehouse'].browse(data.get('warehouse_ids'))
		date_from = datetime.strptime(str(data.get('date_from')), "%Y-%m-%d").strftime("%d-%m-%Y")
		date_to = datetime.strptime(str(data.get('date_to')), "%Y-%m-%d").strftime("%d-%m-%Y")
		company_id = self.env['res.company'].browse(data.get('company_id')[0])
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
		worksheet.merge_range(1, 0, 1, 14, TITLEHEDER,header_format)
		rowscol = 1
		if warehouse_ids:
			for warehouse in warehouse_ids:
				# Report Title
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 3,'Warehouse', title_format)
				worksheet.merge_range((rowscol + 2), 12, (rowscol + 2), 14, str(warehouse.name) , title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 3,'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 3, str(company_id.name) , title_format)

				worksheet.merge_range((rowscol + 4), 5, (rowscol + 4), 7,'Start Date: ', title_format)
				worksheet.merge_range((rowscol + 5), 5, (rowscol + 5), 7, str(start_date) , title_format)

				worksheet.merge_range((rowscol + 4), 12, (rowscol + 4), 14,'End Date:', title_format)
				worksheet.merge_range((rowscol + 5), 12, (rowscol + 5), 14, str(end_date) , title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 2, 'Product Category', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 3, (rowscol + 7), 5, 'Transfers Dates', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 6, (rowscol + 7), 8, 'Source Location', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 9, (rowscol + 7), 11, 'Destination Location', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 12, (rowscol + 7), 14, 'Transfers Location Qty', cell_wrap_format_bold)


				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 2, '', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 3, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 4, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 5, 'Last Adjustment', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 6, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 7, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 8, 'Last Adjustment', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 9, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 10, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 11, 'Last Adjustment', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 12, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 13, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 14, 'Last Adjustment', cell_wrap_format_bold)

				rows = (rowscol + 9)
				sale_location_name = purchase_location_name = adjustment_location_name = ''
				sale_location_dest_name = purchase_location_dest_name = adjustment_location_dest_name = ''
				for records in self.get_warehouse_details(data, warehouse):
					for record in records.get('product_data'):
						sale_line = record.get('sale_order_line')
						purchase_line = record.get('purchase_order_line')
						adjustment_line = record.get('adjustment_line')
						# Source Location
						if sale_line.location_id.location_id:
							sale_location_name = str(sale_line.location_id.location_id.name or '') + '/' + str(sale_line.location_id.name or '') 
						else:
							sale_location_name = str(sale_line.location_id.name or '')

						if purchase_line.location_id.location_id:
							purchase_location_name = str(purchase_line.location_id.location_id.name or '') + '/' + str(purchase_line.location_id.name or '') 
						else:
							purchase_location_name = str(purchase_line.location_id.name or '')

						if adjustment_line.location_id.location_id:
							adjustment_location_name = str(adjustment_line.location_id.location_id.name or '') + '/' + str(adjustment_line.location_id.name or '') 
						else:
							adjustment_location_name = str(adjustment_line.location_id.name or '')

						# Destination Location
						if sale_line.location_dest_id.location_id:
							sale_location_dest_name = str(sale_line.location_dest_id.location_id.name or '') + '/' + str(sale_line.location_dest_id.name or '') 
						else:
							sale_location_dest_name = str(sale_line.location_dest_id.name or '')

						if purchase_line.location_dest_id.location_id:
							purchase_location_dest_name = str(purchase_line.location_dest_id.location_id.name or '') + '/' + str(purchase_line.location_dest_id.name or '') 
						else:
							purchase_location_dest_name = str(purchase_line.location_dest_id.name or '')

						if adjustment_line.location_dest_id.location_id:
							adjustment_location_dest_name = str(adjustment_line.location_dest_id.location_id.name or '') + '/' + str(adjustment_line.location_dest_id.name or '') 
						else:
							adjustment_location_dest_name = str(adjustment_line.location_dest_id.name or '')

						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)
						worksheet.write(rows, 2,  record.get('product_category'), cell_wrap_format)

						sale_line_date = ''
						if sale_line.date:
							sale_line_date = str(sale_line.date.date())
							sale_line_date = datetime.strptime(sale_line_date, '%Y-%m-%d').strftime("%Y-%m-%d")

						purchase_line_date = ''
						if purchase_line.date:
							purchase_line_date = str(purchase_line.date.date())
							purchase_line_date = datetime.strptime(purchase_line_date, '%Y-%m-%d').strftime("%Y-%m-%d")

						adjustment_line_date = ''
						if adjustment_line.date:
							adjustment_line_date = str(adjustment_line.date.date())
							adjustment_line_date = datetime.strptime(adjustment_line_date, '%Y-%m-%d').strftime("%Y-%m-%d")

						worksheet.write(rows, 3,  str(sale_line_date), cell_wrap_format)
						worksheet.write(rows, 4,  str(purchase_line_date), cell_wrap_format)
						worksheet.write(rows, 5,  str(adjustment_line_date), cell_wrap_format)						
						worksheet.write(rows, 6,  sale_location_name, cell_wrap_format)
						worksheet.write(rows, 7,  purchase_location_name, cell_wrap_format)
						worksheet.write(rows, 8,  adjustment_location_name, cell_wrap_format)
						worksheet.write(rows, 9,  sale_location_dest_name, cell_wrap_format)
						worksheet.write(rows, 10, purchase_location_dest_name, cell_wrap_format)
						worksheet.write(rows, 11, adjustment_location_dest_name, cell_wrap_format)
						worksheet.write(rows, 12,  str('%.2f' % sale_line.product_uom_qty), cell_wrap_format_amount_val)
						worksheet.write(rows, 13,  str('%.2f' % purchase_line.product_uom_qty), cell_wrap_format_amount_val)
						worksheet.write(rows, 14,  str('%.2f' % adjustment_line.product_uom_qty), cell_wrap_format_amount_val)
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
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 3,'Location', title_format)
				worksheet.merge_range((rowscol + 2), 12, (rowscol + 2), 14, str(location_name) , title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 3,'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 3, str(company_id.name) , title_format)

				worksheet.merge_range((rowscol + 4), 5, (rowscol + 4), 7,'Start Date: ', title_format)
				worksheet.merge_range((rowscol + 5), 5, (rowscol + 5), 7, str(start_date) , title_format)

				worksheet.merge_range((rowscol + 4), 12, (rowscol + 4), 14,'End Date:', title_format)
				worksheet.merge_range((rowscol + 5), 12, (rowscol + 5), 14, str(end_date) , title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 2, 'Product Category', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 3, (rowscol + 7), 5, 'Transfers Dates', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 6, (rowscol + 7), 8, 'Source Location', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 9, (rowscol + 7), 11, 'Destination Location', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 12, (rowscol + 7), 14, 'Transfers Location Qty', cell_wrap_format_bold)


				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 2, '', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 3, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 4, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 5, 'Last Adjustment', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 6, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 7, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 8, 'Last Adjustment', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 9, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 10, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 11, 'Last Adjustment', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 12, 'Last Sale', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 13, 'Last Purchase', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 14, 'Last Adjustment', cell_wrap_format_bold)

				rows = (rowscol + 9)
				sale_location_name = purchase_location_name = adjustment_location_name = ''
				sale_location_dest_name = purchase_location_dest_name = adjustment_location_dest_name = ''
				for records in self.get_location_details(data, location):
					for record in records.get('product_data'):
						sale_line = record.get('sale_order_line')
						purchase_line = record.get('purchase_order_line')
						adjustment_line = record.get('adjustment_line')
						# Source Location
						if sale_line.location_id.location_id:
							sale_location_name = str(sale_line.location_id.location_id.name or '') + '/' + str(sale_line.location_id.name or '') 
						else:
							sale_location_name = str(sale_line.location_id.name or '')

						if purchase_line.location_id.location_id:
							purchase_location_name = str(purchase_line.location_id.location_id.name or '') + '/' + str(purchase_line.location_id.name or '') 
						else:
							purchase_location_name = str(purchase_line.location_id.name or '')

						if adjustment_line.location_id.location_id:
							adjustment_location_name = str(adjustment_line.location_id.location_id.name or '') + '/' + str(adjustment_line.location_id.name or '') 
						else:
							adjustment_location_name = str(adjustment_line.location_id.name or '')

						# Destination Location
						if sale_line.location_dest_id.location_id:
							sale_location_dest_name = str(sale_line.location_dest_id.location_id.name or '') + '/' + str(sale_line.location_dest_id.name or '') 
						else:
							sale_location_dest_name = str(sale_line.location_dest_id.name or '')

						if purchase_line.location_dest_id.location_id:
							purchase_location_dest_name = str(purchase_line.location_dest_id.location_id.name or '') + '/' + str(purchase_line.location_dest_id.name or '') 
						else:
							purchase_location_dest_name = str(purchase_line.location_dest_id.name or '')

						if adjustment_line.location_dest_id.location_id:
							adjustment_location_dest_name = str(adjustment_line.location_dest_id.location_id.name or '') + '/' + str(adjustment_line.location_dest_id.name or '') 
						else:
							adjustment_location_dest_name = str(adjustment_line.location_dest_id.name or '')

						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)
						worksheet.write(rows, 2,  record.get('product_category'), cell_wrap_format)

						sale_line_date = ''
						if sale_line.date:
							sale_line_date = str(sale_line.date.date())
							sale_line_date = datetime.strptime(sale_line_date, '%Y-%m-%d').strftime("%Y-%m-%d")

						purchase_line_date = ''
						if purchase_line.date:
							purchase_line_date = str(purchase_line.date.date())
							purchase_line_date = datetime.strptime(purchase_line_date, '%Y-%m-%d').strftime("%Y-%m-%d")

						adjustment_line_date = ''
						if adjustment_line.date:
							adjustment_line_date = str(adjustment_line.date.date())
							adjustment_line_date = datetime.strptime(adjustment_line_date, '%Y-%m-%d').strftime("%Y-%m-%d")

						worksheet.write(rows, 3,  str(sale_line_date), cell_wrap_format)
						worksheet.write(rows, 4,  str(purchase_line_date), cell_wrap_format)
						worksheet.write(rows, 5,  str(adjustment_line_date), cell_wrap_format)

						worksheet.write(rows, 6,  sale_location_name, cell_wrap_format)
						worksheet.write(rows, 7,  purchase_location_name, cell_wrap_format)
						worksheet.write(rows, 8,  adjustment_location_name, cell_wrap_format)
						worksheet.write(rows, 9,  sale_location_dest_name, cell_wrap_format)
						worksheet.write(rows, 10, purchase_location_dest_name, cell_wrap_format)
						worksheet.write(rows, 11, adjustment_location_dest_name, cell_wrap_format)
						worksheet.write(rows, 12,  str('%.2f' % sale_line.product_uom_qty), cell_wrap_format_amount_val)
						worksheet.write(rows, 13,  str('%.2f' % purchase_line.product_uom_qty), cell_wrap_format_amount_val)
						worksheet.write(rows, 14,  str('%.2f' % adjustment_line.product_uom_qty), cell_wrap_format_amount_val)
						rows = rows + 1
					rows = rows
				rowscol = rows + 2
		workbook.close()
		buf = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())
		self.document = buf
		self.file = 'Inventory And Stock Location Transfer Report'+'.xlsx'
		return {
			'res_id': self.id,
			'name': 'Files to Download',
			'view_type': 'form',
			"view_mode": 'form,list',
			'res_model': 'stock.location.transfer.warehouse.report',
			'type': 'ir.actions.act_window',
			'target': 'new',
		}