# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command

class PosConfig(models.Model):
	_inherit = 'pos.config'

	restrict_quantity_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_qty_employee_pos_config_rel',
		string="Control de restricción de cantidad",
		help='Los empleados no pueden acceder al botón de cantidad')
	restrict_discount_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_discount_employee_pos_config_rel', 
		string="Restringir el control de descuentos",
		help='Los empleados no pueden acceder al botón de descuento')
	restrict_price_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_price_employee_pos_config_rel', 
		string="Restringir el control de precios",
		help='Los empleados no pueden acceder al botón de precios')
	restrict_pricelist_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_pricelist_employee_pos_config_rel', 
		string="Restringir el control de lista de precios",
		help='Los empleados no pueden acceder a la lista de precios')
	restrict_remove_line_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_remove_line_employee_pos_config_rel', 
		string="Restringir eliminar control de línea",
		help='Los empleados no pueden acceder al botón Eliminar línea')
	restrict_plus_minus_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_plu_min_employee_pos_config_rel', 
		string="Restringir +/- Control",
		help='Los empleados no pueden acceder a (+/-) botón')
	restrict_decimal_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_decimal_employee_pos_config_rel', 
		string="Restringir (,)",
		help='Los empleados no pueden acceder al botón (,)')
	restrict_numpad_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_numpad_employee_pos_config_rel', 
		string="Restringir teclado en pantalla",
		help='Los empleados no pueden acceder al teclado en pantalla')
	restrict_cancel_order_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_cancel_order_employee_pos_config_rel', 
		string="Restringir el control de órdenes de cancelación",
		help='Los empleados no pueden acceder al botón cancelar pedido')
	restrict_cash_in_out_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_cash_in_out_employee_pos_config_rel', 
		string="Restringir el control de entrada y salida de efectivo",
		help='Los empleados no pueden acceder al botón de entrada y salida de efectivo')
	restrict_refund_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_refund_employee_pos_config_rel', 
		string="Restringir el control de órdenes de reembolso",
		help='Los empleados no pueden acceder a reembolsos')
	restrict_reprintinvoice_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_reprintinvoice_employee_pos_config_rel', 
		string="Restringir la reimpresión de la factura",
		help='Los empleados no pueden reimprimir facturas')
	restrict_print_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_print_employee_pos_config_rel', 
		string="Restringir el control de impresión",
		help='Los empleados no pueden acceder a realizar impresiones')
	restrict_payment_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_payment_employee_pos_config_rel', 
		string="Restringir el control de pago",
		help='Los empleados no pueden acceder a pago')
	restrict_actiondiscount_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_actiondiscount_employee_pos_config_rel', 
		string="Restringir el boton de descuentos",
		help='Los empleados no pueden acceder al botón de descuento')
	restrict_transfer_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_transfer_employee_pos_config_rel', 
		string="Restringir el boton de Transferir / Fusionar",
		help='Los empleados no pueden acceder al botón de Transferir / Fusionar')
	restrict_partner_employee_ids = fields.Many2many(
		'hr.employee', 
		relation='restrict_partner_employee_pos_config_rel', 
		string="Restringir el control de cliente",
		help='Los empleados no pueden acceder a cliente')
	allow_pdf_download = fields.Boolean('Permitir descarga de PDF', default=True)
	pos_customer_id = fields.Many2one('res.partner', string='Cliente por defecto')
	pos_invoice_default = fields.Boolean('POS Factura marcada por defecto', default=False)


	@api.onchange('basic_employee_ids','advanced_employee_ids')
	def _onchange_restrict_access_employee_ids(self):
		config_employee_ids = self.basic_employee_ids + self.advanced_employee_ids
		
		restrict_quantity_employee_ids = self.restrict_quantity_employee_ids
		for employee in restrict_quantity_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_quantity_employee_ids -= employee

		restrict_discount_employee_ids = self.restrict_discount_employee_ids
		for employee in restrict_discount_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_discount_employee_ids -= employee

		restrict_price_employee_ids = self.restrict_price_employee_ids
		for employee in restrict_price_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_price_employee_ids -= employee

		restrict_pricelist_employee_ids = self.restrict_pricelist_employee_ids
		for employee in restrict_pricelist_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_pricelist_employee_ids -= employee

		restrict_remove_line_employee_ids = self.restrict_remove_line_employee_ids
		for employee in restrict_remove_line_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_remove_line_employee_ids -= employee

		restrict_plus_minus_employee_ids = self.restrict_plus_minus_employee_ids
		for employee in restrict_plus_minus_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_plus_minus_employee_ids -= employee
				
		restrict_decimal_employee_ids = self.restrict_decimal_employee_ids
		for employee in restrict_decimal_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_decimal_employee_ids -= employee

		restrict_numpad_employee_ids = self.restrict_numpad_employee_ids
		for employee in restrict_numpad_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_numpad_employee_ids -= employee

		restrict_cancel_order_employee_ids = self.restrict_cancel_order_employee_ids
		for employee in restrict_cancel_order_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_cancel_order_employee_ids -= employee

		restrict_cash_in_out_employee_ids = self.restrict_cash_in_out_employee_ids
		for employee in restrict_cash_in_out_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_cash_in_out_employee_ids -= employee

		restrict_refund_employee_ids = self.restrict_refund_employee_ids
		for employee in restrict_refund_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_refund_employee_ids -= employee
		restrict_reprintinvoice_employee_ids = self.restrict_reprintinvoice_employee_ids
		for employee in restrict_reprintinvoice_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_reprintinvoice_employee_ids -= employee
				
		restrict_print_employee_ids = self.restrict_print_employee_ids
		for employee in restrict_print_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_print_employee_ids -= employee

		restrict_payment_employee_ids = self.restrict_payment_employee_ids
		for employee in restrict_payment_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_payment_employee_ids -= employee

		restrict_actiondiscount_employee_ids = self.restrict_actiondiscount_employee_ids
		for employee in restrict_actiondiscount_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_actiondiscount_employee_ids -= employee

		restrict_transfer_employee_ids = self.restrict_transfer_employee_ids
		for employee in restrict_transfer_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_transfer_employee_ids -= employee

		restrict_partner_employee_ids = self.restrict_partner_employee_ids
		for employee in restrict_partner_employee_ids:
			if employee not in config_employee_ids:
				self.restrict_partner_employee_ids -= employee
