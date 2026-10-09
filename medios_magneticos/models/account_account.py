
from odoo import models, fields, api
from lxml import etree    
from odoo.exceptions import UserError, ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    concepto = fields.Char(string='Concepto')
    plantilla = fields.Char(string='Plantilla')
    categoria = fields.Char(string='Categoría')
    tipo_operacion = fields.Selection([
        ('debito_credito', 'Saldo Débito - Crédito'),
        ('credito', 'Saldo Crédito'),
        ('debito', 'Saldo Débito'),
        ('saldo_final', 'Saldo Final'),
        ('movimiento_periodo', 'Movimiento del Periodo'),
        ('saldo_inicial', 'Saldo Inicial')], string='Tipo de Operación')


class TuModeloExogena(models.Model):
    _name = 'account.exogena'
    _description = 'Información Exógena'

    # wizard_id = fields.Many2one('wizard.configuracion.exogena', string="Wizard")
    year = fields.Integer('Año')
    cuenta = fields.Char('Cuenta')
    concepto = fields.Char('Concepto')
    formato = fields.Selection([
        ('1001', '1001'), ('1003', '1003'), ('1004', '1004'),
        ('1005', '1005'), ('1006', '1006'), ('1007', '1007'),
        ('1008', '1008'), ('1009', '1009'), ('1010', '1010'),
        ('1011', '1011'), ('1012', '1012'), ('1647', '1647'),
        ('2275', '2275'), ('2276', '2276'),
    ], string='Formato')
    valor = fields.Float('Valor')
    tipo_suma = fields.Selection(
        [('suma_debitos','1. Suma debitos'),
         ('suma_creditos','2. Suma creditos'),
         ('debitos_creditos','3. Debitos - creditos'),
         ('saldo_general','4. Saldo general'),
         ('saldo_inicial','5. Saldo inicial'),],
        'Tipo de suma')
    categoria = fields.Char('Categoría')
