from odoo import models, fields
from odoo import _

class EmployeeFunctions(models.Model):
    _name = "hr.employee.functions"
    _description = "Almacena las funciones de los empleados"
    
    employee_id = fields.Many2one("hr.employee", 'Employee', required=True)
    name = fields.Text(required=True)
    