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

class StockMovementReport(models.TransientModel):
	_name = 'stock.movement.warehouse.report'
	_description = 'Inventory And Stock Movement Report'

	date_from = fields.Date('Start Date')
	date_to = fields.Date('End Date')
	warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
	location_ids = fields.Many2many('stock.location', string="Location")
	document = fields.Binary('File To Download')
	file = fields.Char('Report File Name', readonly=1)
	company_id = fields.Many2one('res.company','Company')
	report_type = fields.Selection([('warehouse','Warehouse'),('location','Location')], default='warehouse', string='Generate Report Based on')

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
			 'model': 'stock.movement.warehouse.report',
			 'form': data
		}
		return self.env.ref('warehouse_report_app.action_report_stock_movement').report_action(self, data=datas)


# Warehouse

	def _get_stock_move_details_info(self, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		domain_quant += ['|',('warehouse_id', '=', warehouse_id),('picking_type_id.warehouse_id', '=', warehouse_id)]
		stock_move_ids =self.env['stock.move'].search(domain_quant)
		return stock_move_ids


	def get_warehouse_details(self, data, warehouse):
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
				if move.date:
					move_date = move.date.date()
				else:
					move_date = ''

				value.update({
					'move_id'				: move.id,
					'product_name'         	: product_name or '',
					'product_code'         	: move.product_id.default_code or '',
					'product_category'     	: move.product_id.categ_id.complete_name  or '',
					'inventory_date'		: move_date,
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


	def get_location_details(self, data, location):
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

				if move.date:
					move_date = move.date.date()
				else:
					move_date = ''

				value.update({
					'move_id'				: move.id,
					'product_name'         	: product_name or '',
					'product_code'         	: move.product_id.default_code or '',
					'product_category'     	: move.product_id.categ_id.complete_name  or '',
					'inventory_date'		: move_date,
					'picking_type'			: picking_type_name,
					'source_location'		: move.location_id,
					'dest_location'			: move.location_dest_id,
					'product_uom_qty'		: move.product_uom_qty,
				})
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines


	def print_excel_report(self):
		self.ensure_one()
		[data] = self.read()
		file_path = 'Inventory And Stock Movement Report' + '.xlsx'
		workbook = xlsxwriter.Workbook('/tmp/' + file_path)
		worksheet = workbook.add_worksheet('Inventory And Stock Movement Report')

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
		TITLEHEDER = 'Inventory And Stock Movement Report' 
		worksheet.set_column(0, 7, 30)

		ware_obj = self.env['stock.warehouse']
		location_obj = self.env['stock.location']

		start_date = datetime.strptime(str(data.get('date_from')), "%Y-%m-%d").strftime("%Y-%m-%d")
		end_date = datetime.strptime(str(data.get('date_to')), "%Y-%m-%d").strftime("%Y-%m-%d")
		location_ids  = self.env['stock.location'].browse(data.get('location_ids'))
		warehouse_ids = self.env['stock.warehouse'].browse(data.get('warehouse_ids'))
		date_from = datetime.strptime(str(data.get('date_from')), "%Y-%m-%d").strftime("%d-%m-%Y")
		date_to = datetime.strptime(str(data.get('date_to')), "%Y-%m-%d").strftime("%d-%m-%Y")
		company_id = self.env['res.company'].browse(data.get('company_id')[0])
		data  = { 
			'start_date'    : start_date,
			'end_date'    	: end_date,
			'date_from'     : date_from,
			'date_to'     	: date_to,
			'warehouse_ids' : warehouse_ids,
			'location_ids'  : location_ids,
			'company_id'	: company_id
		}
		worksheet.merge_range(1, 0, 1, 7, TITLEHEDER,header_format)
		rowscol = 1
		if warehouse_ids:
			for warehouse in warehouse_ids:
				# Report Title
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 2,'Warehouse', title_format)
				worksheet.merge_range((rowscol + 2), 5, (rowscol + 2), 7, str(warehouse.name) , title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 1,'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 1, str(company_id.name) , title_format)

				worksheet.merge_range((rowscol + 4), 3, (rowscol + 4), 4,'Start Date: ', title_format)
				worksheet.merge_range((rowscol + 5), 3, (rowscol + 5), 4, str(start_date) , title_format)

				worksheet.merge_range((rowscol + 4), 5, (rowscol + 4), 7,'End Date:', title_format)
				worksheet.merge_range((rowscol + 5), 5, (rowscol + 5), 7, str(end_date) , title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 2, 'Product Category', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 3, 'Inventory Date', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 4, 'Operation Types', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 5, (rowscol + 7), 6, 'Locations', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 7, 'Qty', cell_wrap_format_bold)


				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 2, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 3, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 4, '', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 5, 'Source', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 6, 'Destination', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 7, '', cell_wrap_format_bold)				

				rows = (rowscol + 9)
				for records in self.get_warehouse_details(data, warehouse):
					for record in records.get('product_data'):
						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)
						worksheet.write(rows, 2,  record.get('product_category'), cell_wrap_format)						

						inventory_date = datetime.strptime(str(record.get('inventory_date')), '%Y-%m-%d').strftime("%Y-%m-%d")
						worksheet.write(rows, 3,  inventory_date, cell_wrap_format)
						
						worksheet.write(rows, 4,  record.get('picking_type'), cell_wrap_format)

						if record.get('source_location').location_id:
							source_location_name = str(record.get('source_location').location_id.name or '') + '/' + str(record.get('source_location').name or '') 
						else:
							source_location_name = str(record.get('source_location').name or '')

						if record.get('dest_location').location_id:
							dest_location_name = str(record.get('dest_location').location_id.name or '') + '/' + str(record.get('dest_location').name or '') 
						else:
							dest_location_name = str(record.get('dest_location').name or '') 

						worksheet.write(rows, 5,  source_location_name, cell_wrap_format)
						worksheet.write(rows, 6,  dest_location_name, cell_wrap_format)
						worksheet.write(rows, 7,  str('%.2f' % record.get('product_uom_qty')), cell_wrap_format_amount_val)
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
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 2,'Location', title_format)
				worksheet.merge_range((rowscol + 2), 5, (rowscol + 2), 7, str(location_name) , title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 1,'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 1, str(company_id.name) , title_format)

				worksheet.merge_range((rowscol + 4), 3, (rowscol + 4), 4,'Start Date: ', title_format)
				worksheet.merge_range((rowscol + 5), 3, (rowscol + 5), 4, str(start_date) , title_format)

				worksheet.merge_range((rowscol + 4), 5, (rowscol + 4), 7,'End Date:', title_format)
				worksheet.merge_range((rowscol + 5), 5, (rowscol + 5), 7, str(end_date) , title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 2, 'Product Category', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 3, 'Inventory Date', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 4, 'Operation Types', cell_wrap_format_bold)
				worksheet.merge_range((rowscol + 7), 5, (rowscol + 7), 6, 'Locations', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 7, 'Qty', cell_wrap_format_bold)


				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 2, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 3, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 4, '', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 5, 'Source', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 6, 'Destination', cell_wrap_format_bold)

				worksheet.write((rowscol + 8), 7, '', cell_wrap_format_bold)				

				rows = (rowscol + 9)
				for records in self.get_location_details(data, location):
					for record in records.get('product_data'):
						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)
						worksheet.write(rows, 2,  record.get('product_category'), cell_wrap_format)

						inventory_date = datetime.strptime(str(record.get('inventory_date')), '%Y-%m-%d').strftime("%Y-%m-%d")
						worksheet.write(rows, 3,  inventory_date, cell_wrap_format)
						
						worksheet.write(rows, 4,  record.get('picking_type'), cell_wrap_format)

						if record.get('source_location').location_id:
							source_location_name = str(record.get('source_location').location_id.name or '') + '/' + str(record.get('source_location').name or '') 
						else:
							source_location_name = str(record.get('source_location').name or '')

						if record.get('dest_location').location_id:
							dest_location_name = str(record.get('dest_location').location_id.name or '') + '/' + str(record.get('dest_location').name or '') 
						else:
							dest_location_name = str(record.get('dest_location').name or '') 

						worksheet.write(rows, 5,  source_location_name, cell_wrap_format)
						worksheet.write(rows, 6,  dest_location_name, cell_wrap_format)
						worksheet.write(rows, 7,  str('%.2f' % record.get('product_uom_qty')), cell_wrap_format_amount_val)
						rows = rows + 1
					rows = rows
				rowscol = rows + 2
		workbook.close()
		buf = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())
		self.document = buf
		self.file = 'Inventory And Stock Movement Report'+'.xlsx'
		return {
			'res_id': self.id,
			'name': 'Files to Download',
			'view_type': 'form',
			"view_mode": 'form,list',
			'res_model': 'stock.movement.warehouse.report',
			'type': 'ir.actions.act_window',
			'target': 'new',
		}