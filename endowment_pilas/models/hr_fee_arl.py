from odoo import models, fields, api

class HrFeeArl(models.Model):
    _name = 'hr.fee.arl'
    _description = 'Tarifas por Clase de Riesgo ARL'
    _order = 'code'

    code = fields.Selection([
        ('1', 'Clase I'),
        ('2', 'Clase II'),
        ('3', 'Clase III'),
        ('4', 'Clase IV'),
        ('5', 'Clase V'),
    ], string='Clase de Riesgo', required=True, copy=False)
    
    percentage = fields.Float(string='Arl (%)', required=True,digits=(16, 3) )
    name = fields.Char(string='Descripción', store=True)

