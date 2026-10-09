from odoo import models, fields

class HrCertifiedConcept(models.Model):
    _name = "hr.certified.concept"
    _description = "Modelo que permite almacenar los conceptos para las reglas salariales"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    type = fields.Selection([("1","Ingresos"),("2","Aportes")], string="Type")
    is_print = fields.Boolean(default=True, string="Is Print")