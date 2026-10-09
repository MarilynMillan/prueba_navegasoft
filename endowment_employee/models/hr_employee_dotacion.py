from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrEmployeeDotacion(models.Model):
    _name = "hr.employee.dotacion"
    _description = "Dotación entregada a empleados"
    

    employee_id = fields.Many2one("hr.employee", string="Empleado")
    product_id = fields.Many2one("product.product",string="Producto")
    picking_id = fields.Many2one("stock.picking",string="Orden de Albarán")
    cost = fields.Float(string="Monto")
    date = fields.Date(default=fields.Date.context_today,string="Fecha")
    payroll_id = fields.Many2one("hr.payslip", string="Nómina relacionada")