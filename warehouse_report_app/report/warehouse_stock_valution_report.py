# -*- coding: utf-8 -*-


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, api,fields
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round


class InventoryValutionReport(models.AbstractModel):
	_name = 'report.warehouse_report_app.report_stockvalutioninfo' 
	_description = 'Inventory And Stock Valuation Report'

# Warehouse



	# ***********************************************************************
	# Previous Month
	def _get_prev_product_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_product_in_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_return_in_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id.usage', '=', 'internal'),('location_dest_id.usage', '=', 'internal')]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_return_out_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id.usage', '=', 'internal'),('location_dest_id.usage', '=', 'internal')]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_adjusted_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('location_id.usage', '=', 'inventory')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_scrap_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('location_dest_id.usage', '=', 'inventory')]
		domain_quant += [('location_id.usage', '=', 'internal')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	# ***********************************************************************
	# Current Month
	def _get_product_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_product_in_info(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming'), ('picking_type_id.warehouse_id', '=', warehouse_id)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_return_in_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id.usage', '=', 'internal'),('location_dest_id.usage', '=', 'internal')]
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
		domain_quant += ['|',('location_id.usage', '=', 'internal'),('location_dest_id.usage', '=', 'internal')]
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

	def _get_scrap_qty(self, product_id, warehouse_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += [('location_dest_id.usage', '=', 'inventory')]
		domain_quant += [('location_id.usage', '=', 'internal')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

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

				# /*------------------------------------------------------------------*\
				# Previous Month

				curr_date_from = datetime.strptime(data.get('date_from'), "%d-%m-%Y")
				curr_date_to = datetime.strptime(data.get('date_to'), "%d-%m-%Y")

				prev_start_date_data = curr_date_from - relativedelta(months=1)
				# prev_start_date_data = prev_start_date_data + ' 00:00:00'
				prev_end_date_data 	 = curr_date_to - relativedelta(months=1)

				prev_delivered_qty_total = self._get_prev_product_info(product_id.id, warehouse_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_received_qty_total = self._get_prev_product_in_info(product_id.id, warehouse_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_return_in_qty_total = self._get_prev_return_in_qty(product_id.id, warehouse_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_return_out_qty_total = self._get_prev_return_out_qty(product_id.id, warehouse_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_adjusted_qty_total = self._get_prev_adjusted_qty(product_id.id, warehouse_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_scrap_qty = self._get_prev_scrap_qty(product_id.id, warehouse_id, prev_start_date_data, prev_end_date_data, company_id)

				# Opening Stock
				prev_adjusted_qty_on_hand = prev_adjusted_qty_total
				prev_received_qty_on_hand = prev_received_qty_total + prev_return_in_qty_total
				prev_delivered_qty_on_hand = prev_delivered_qty_total + prev_return_out_qty_total
				

				opening_stock =  (prev_received_qty_on_hand - prev_delivered_qty_on_hand + prev_adjusted_qty_on_hand - prev_scrap_qty)
				# /*------------------------------------------------------------------*\
				# Current Month

				delivered_qty = self._get_product_info(product_id.id, warehouse_id, start_date, end_date, company_id)
				received_qty = self._get_product_in_info(product_id.id, warehouse_id, start_date, end_date, company_id)
				return_in_qty = self._get_return_in_qty(product_id.id, warehouse_id, start_date, end_date, company_id)
				return_out_qty = self._get_return_out_qty(product_id.id, warehouse_id, start_date, end_date, company_id)
				adjusted_qty = self._get_adjusted_qty(product_id.id, warehouse_id, start_date, end_date, company_id)
				scrap_qty = self._get_scrap_qty(product_id.id, warehouse_id, start_date, end_date, company_id)


				adjusted_qty_on_hand = adjusted_qty
				received_qty_on_hand = received_qty + return_in_qty
				delivered_qty_on_hand = delivered_qty + return_out_qty

				adjusted_qty_hand_key = col + 'adjustment' + str(counter)
				received_qty_hand_key = col + 'received' + str(counter)
				delivered_qty_hand_key = col + 'delivered' + str(counter)


				ending_stock =  opening_stock + received_qty_on_hand - delivered_qty_on_hand + adjusted_qty_on_hand - scrap_qty
				total_value = (ending_stock * price_used)

				value.update({
					adjusted_qty_hand_key : adjusted_qty_on_hand,
					received_qty_hand_key : received_qty_on_hand,
					delivered_qty_hand_key : delivered_qty_on_hand,
				})
				
				value.update({
					'product_id'         : product_id.id,
					'product_name'       : product_name or '',
					'product_code'       : product_id.default_code or '',
					'cost_price'         : product_id.standard_price  or 0.00,
					'sales_price'   	 : product_id.list_price  or '',
					'product_category'   : product_id.categ_id.complete_name  or '',
					'qty_available'   	 : product_id.qty_available  or '',
					'opening_stock'		 : opening_stock,
					'ending_stock'		 : ending_stock,
					'total_value'		 : total_value,
					'scrap_qty'			 : scrap_qty,
				})
				product_data.append(value)
			lines.append({'product_data':product_data})
		return lines

# Location


	def _get_prev_location_product_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_location_product_in_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_location_return_in_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_location_return_out_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_prev_location_adjusted_qty(self, product_id, location_id, start_date, end_date, company_id):
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

	def _get_prev_location_scrap_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('location_dest_id.usage', '=', 'inventory')]
		domain_quant += [('location_id.usage', '=', 'internal')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0


	# ***********************************************************************
	# Current Month
	def _get_location_product_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_location_product_in_info(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_location_return_in_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'incoming')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_location_return_out_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('origin_returned_move_id', '!=', False)]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date), ('picking_type_id.code', '=', 'outgoing')]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

	def _get_location_adjusted_qty(self, product_id, location_id, start_date, end_date, company_id):
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

	def _get_location_scrap_qty(self, product_id, location_id, start_date, end_date, company_id):
		domain_quant = [('product_id', '=', product_id), ('state', '=', 'done'), ('company_id', '=', company_id)]
		domain_quant += ['|',('location_id','=', location_id) , ('location_dest_id','=', location_id)]
		domain_quant += [('location_dest_id.usage', '=', 'inventory')]
		domain_quant += [('location_id.usage', '=', 'internal')]
		domain_quant += [('date', '>=', start_date), ('date', '<=', end_date)]
		move_ids =self.env['stock.move'].search(domain_quant)
		result = sum([x.product_uom_qty for x in move_ids])
		if result:
			return result
		else:
			return 0.0

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
			location_id = location.id
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

				# /*------------------------------------------------------------------*\
				# Previous Month

				curr_date_from = datetime.strptime(data.get('date_from'), "%d-%m-%Y")
				curr_date_to = datetime.strptime(data.get('date_to'), "%d-%m-%Y")

				prev_start_date_data = curr_date_from - relativedelta(months=1)
				# prev_start_date_data = prev_start_date_data + ' 00:00:00'
				prev_end_date_data 	 = curr_date_to - relativedelta(months=1)

				prev_delivered_qty_total = self._get_prev_location_product_info(product_id.id, location_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_received_qty_total = self._get_prev_location_product_in_info(product_id.id, location_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_return_in_qty_total = self._get_prev_location_return_in_qty(product_id.id, location_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_return_out_qty_total = self._get_prev_location_return_out_qty(product_id.id, location_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_adjusted_qty_total = self._get_prev_location_adjusted_qty(product_id.id, location_id, prev_start_date_data, prev_end_date_data, company_id)
				prev_scrap_qty = self._get_prev_location_scrap_qty(product_id.id, location_id, prev_start_date_data, prev_end_date_data, company_id)

				# Opening Stock
				prev_adjusted_qty_on_hand = prev_adjusted_qty_total
				prev_received_qty_on_hand = prev_received_qty_total + prev_return_in_qty_total
				prev_delivered_qty_on_hand = prev_delivered_qty_total + prev_return_out_qty_total
				

				opening_stock =  (prev_received_qty_on_hand - prev_delivered_qty_on_hand + prev_adjusted_qty_on_hand - prev_scrap_qty)
				# /*------------------------------------------------------------------*\
				# Current Month

				delivered_qty = self._get_location_product_info(product_id.id, location_id, start_date, end_date, company_id)
				received_qty = self._get_location_product_in_info(product_id.id, location_id, start_date, end_date, company_id)
				return_in_qty = self._get_location_return_in_qty(product_id.id, location_id, start_date, end_date, company_id)
				return_out_qty = self._get_location_return_out_qty(product_id.id, location_id, start_date, end_date, company_id)
				adjusted_qty = self._get_location_adjusted_qty(product_id.id, location_id, start_date, end_date, company_id)
				scrap_qty = self._get_location_scrap_qty(product_id.id, location_id, start_date, end_date, company_id)

				adjusted_qty_on_hand = adjusted_qty
				received_qty_on_hand = received_qty + return_in_qty
				delivered_qty_on_hand = delivered_qty + return_out_qty

				adjusted_qty_hand_key = col + 'adjustment' + str(counter)
				received_qty_hand_key = col + 'received' + str(counter)
				delivered_qty_hand_key = col + 'delivered' + str(counter)


				ending_stock =  opening_stock + received_qty_on_hand - delivered_qty_on_hand + adjusted_qty_on_hand - scrap_qty
				total_value = (ending_stock * price_used)

				value.update({
					adjusted_qty_hand_key : adjusted_qty_on_hand,
					received_qty_hand_key : received_qty_on_hand,
					delivered_qty_hand_key : delivered_qty_on_hand,
				})
				
				value.update({
					'product_id'         : product_id.id,
					'product_name'       : product_name or '',
					'product_code'       : product_id.default_code or '',
					'cost_price'         : product_id.standard_price  or 0.00,
					'sales_price'   	 : product_id.list_price  or '',
					'product_category'   : product_id.categ_id.complete_name  or '',
					'qty_available'   	 : product_id.qty_available  or '',
					'opening_stock'		 : opening_stock,
					'ending_stock'		 : ending_stock,
					'total_value'		 : total_value,
					'scrap_qty'			 : scrap_qty,
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
				   'doc_model': 'inventory.stock.valution.report.wizard',
				   'data': data,
				   'get_warehouse_details':self._get_warehouse_details,
				   'get_location_details':self._get_location_details,
				   }
		return docargs