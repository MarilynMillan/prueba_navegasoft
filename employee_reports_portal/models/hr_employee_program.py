from odoo import models, fields
from odoo import _

class EmployeeProgram(models.Model):
    _name = "hr.employee.program"
    _description = "Almacena los programas de formación de los empleados"
    
    name = fields.Char(string="Program Name", required=True)
    employee_ids = fields.Many2many("hr.employee", 'employee_program_rel', 'program_id', 'employee_id', string="Employees")
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Program name already exists !"),
    ]