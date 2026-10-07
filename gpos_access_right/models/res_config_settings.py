# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	pos_restrict_quantity_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_quantity_employee_ids',
		relation='restrict_qty_employee_res_config_settings_rel', 
		string="Control de restricción de cantidad",
		help='Los empleados no pueden acceder al botón de cantidad',
		readonly=False)
	pos_restrict_discount_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_discount_employee_ids',
		relation='restrict_discount_employee_res_config_settings_rel', 
		string="Control de restricción de descuento",
		help='Los empleados no pueden acceder al botón de descuento',
		readonly=False)
	pos_restrict_price_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_price_employee_ids',
		relation='restrict_price_employee_res_config_settings_rel', 
		string="Control de restricción de precio",
		help='Los empleados no pueden acceder al botón de precio',
		readonly=False)
	pos_restrict_pricelist_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_pricelist_employee_ids',
		relation='restrict_pricelist_employee_res_config_settings_rel', 
		string="Control de restricción de lista de precio",
		help='Los empleados no pueden acceder a la lista de precio',
		readonly=False)
	pos_restrict_remove_line_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_remove_line_employee_ids',
		relation='restrict_remove_line_employee_res_config_settings_rel', 
		string="Control de restricción de eliminar líneas",
		help='Los empleados no pueden acceder al botón de eliminar líneas',
		readonly=False)
	pos_restrict_plus_minus_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_plus_minus_employee_ids',
		relation='restrict_plu_min_employee_res_config_settings_rel', 
		string="Control de restricción +/-",
		help='Los empleados no pueden acceder al botón de (+/-)',
		readonly=False)
	pos_restrict_decimal_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_decimal_employee_ids',
		relation='restrict_decimal_employee_res_config_settings_rel', 
		string="Control de restricción +/-",
		help='Los empleados no pueden acceder al botón de (+/-)',
		readonly=False)
	pos_restrict_numpad_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_numpad_employee_ids',
		relation='restrict_numpad_employee_res_config_settings_rel', 
		string="Control de restricción teclado en pantalla",
		help='Los empleados no pueden acceder al teclado en pantalla',
		readonly=False)
	pos_restrict_cancel_order_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_cancel_order_employee_ids',
		relation='restrict_cancel_order_employee_res_config_settings_rel', 
		string="Control de restricción de cancelar orden",
		help='Los empleados no pueden acceder al botón cancelar orden',
		readonly=False)
	pos_restrict_cash_in_out_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_cash_in_out_employee_ids', 
		relation='restrict_cash_in_out_employee_res_config_settings_rel', 
		string="Control de restricción de entrada y salida de efectivo",
		help='Los empleados no pueden acceder al botón de entrada y salida de efectivo',
		readonly=False)
	pos_restrict_refund_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_refund_employee_ids',
		relation='restrict_refund_employee_pos_config_rel', 
		string="Control de restricción de reembolso",
		help='Los empleados no pueden acceder al botón de reembolso',
		readonly=False)
	pos_restrict_reprintinvoice_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_reprintinvoice_employee_ids',
		relation='restrict_reprintinvoice_employee_pos_config_rel', 
		string="Control de restricción de reimpresión de factura",
		help='Los empleados no pueden acceder al botón de reimpresión de factura',
		readonly=False)
	pos_restrict_print_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_print_employee_ids',
		relation='restrict_print_employee_pos_config_rel', 
		string="Control de restricción de impresión",
		help='Los empleados no pueden acceder al botón de ordenes de impresión',
		readonly=False)
	pos_restrict_payment_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_payment_employee_ids',
		relation='restrict_payment_employee_pos_config_rel', 
		string="Control de restricción de pago",
		help='Los empleados no pueden acceder al botón de pago',
		readonly=False)
	pos_restrict_partner_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_partner_employee_ids',
		relation='restrict_partner_employee_pos_config_rel', 
		string="Control de restricción de cliente",
		help='Los empleados no pueden acceder a clientes',
		readonly=False)
	pos_restrict_actiondiscount_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_actiondiscount_employee_ids',
		relation='restrict_actiondiscount_employee_res_config_settings_rel', 
		string="Control de restricción de boton de descuento",
		help='Los empleados no pueden acceder al botón de descuento',
		readonly=False)
	pos_restrict_transfer_employee_ids = fields.Many2many(
		related='pos_config_id.restrict_transfer_employee_ids',
		relation='restrict_transfer_employee_res_config_settings_rel', 
		string="Control de restricción de boton de Transferir / Fusionar",
		help='Los empleados no pueden acceder al botón de Transferir / Fusionar',
		readonly=False)
	pos_allow_pdf_download = fields.Boolean(related='pos_config_id.allow_pdf_download', readonly=False)
	pos_customer_id = fields.Many2one('res.partner', related='pos_config_id.pos_customer_id', readonly=False)
	pos_invoice_default = fields.Boolean(related='pos_config_id.pos_invoice_default', readonly=False)
	

	@api.onchange('pos_basic_employee_ids','pos_advanced_employee_ids')
	def _onchange_pos_restrict_access_employee_ids(self):
		config_employee_ids = self.pos_basic_employee_ids + self.pos_advanced_employee_ids
		
		pos_restrict_quantity_employee_ids = self.pos_restrict_quantity_employee_ids
		for employee in pos_restrict_quantity_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_quantity_employee_ids -= employee

		pos_restrict_discount_employee_ids = self.pos_restrict_discount_employee_ids
		for employee in pos_restrict_discount_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_discount_employee_ids -= employee

		pos_restrict_price_employee_ids = self.pos_restrict_price_employee_ids
		for employee in pos_restrict_price_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_price_employee_ids -= employee

		pos_restrict_pricelist_employee_ids = self.pos_restrict_pricelist_employee_ids
		for employee in pos_restrict_pricelist_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_pricelist_employee_ids -= employee

		pos_restrict_remove_line_employee_ids = self.pos_restrict_remove_line_employee_ids
		for employee in pos_restrict_remove_line_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_remove_line_employee_ids -= employee

		pos_restrict_plus_minus_employee_ids = self.pos_restrict_plus_minus_employee_ids
		for employee in pos_restrict_plus_minus_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_plus_minus_employee_ids -= employee

		pos_restrict_decimal_employee_ids = self.pos_restrict_decimal_employee_ids
		for employee in pos_restrict_decimal_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_decimal_employee_ids -= employee

		pos_restrict_numpad_employee_ids = self.pos_restrict_numpad_employee_ids
		for employee in pos_restrict_numpad_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_numpad_employee_ids -= employee

		pos_restrict_cancel_order_employee_ids = self.pos_restrict_cancel_order_employee_ids
		for employee in pos_restrict_cancel_order_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_cancel_order_employee_ids -= employee

		pos_restrict_cash_in_out_employee_ids = self.pos_restrict_cash_in_out_employee_ids
		for employee in pos_restrict_cash_in_out_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_cash_in_out_employee_ids -= employee

		pos_restrict_refund_employee_ids = self.pos_restrict_refund_employee_ids
		for employee in pos_restrict_refund_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_refund_employee_ids -= employee
		pos_restrict_reprintinvoice_employee_ids = self.pos_restrict_reprintinvoice_employee_ids
		for employee in pos_restrict_reprintinvoice_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_reprintinvoice_employee_ids -= employee
		pos_restrict_print_employee_ids = self.pos_restrict_print_employee_ids
		for employee in pos_restrict_print_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_print_employee_ids -= employee
		pos_restrict_payment_employee_ids = self.pos_restrict_payment_employee_ids
		for employee in pos_restrict_payment_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_payment_employee_ids -= employee
		pos_restrict_partner_employee_ids = self.pos_restrict_partner_employee_ids
		for employee in pos_restrict_partner_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_partner_employee_ids -= employee
		pos_restrict_actiondiscount_employee_ids = self.pos_restrict_actiondiscount_employee_ids
		for employee in pos_restrict_actiondiscount_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_actiondiscount_employee_ids -= employee

		pos_restrict_transfer_employee_ids = self.pos_restrict_transfer_employee_ids
		for employee in pos_restrict_transfer_employee_ids:
			if employee not in config_employee_ids:
				self.pos_restrict_transfer_employee_ids -= employee
