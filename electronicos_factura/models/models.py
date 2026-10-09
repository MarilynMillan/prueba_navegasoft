# -*- coding: utf-8 -*-
from odoo import models, fields, modules,tools , api,_ 
import os
import requests
import json 
from odoo.exceptions import AccessError, UserError,  ValidationError
import babel

import time
from dateutil import relativedelta
from datetime import datetime, timedelta
from datetime import time as datetime_time


class datos_generales(models.Model):
    _name= 'electronicos_factura.datos_generales'
    _descripcion='electronicos_factura.datos_generales'

    name = fields.Char("Nombre")
    company_id = fields.Many2one('res.company', string='Compañia', readonly=True, copy=False,
        default=lambda self: self.env['res.company']._company_default_get())
        #states={'draft': [('readonly', False)]})

    diario = fields.Many2one('account.journal', string='Diario',ondelete='restrict')
    tipo_factura = fields.Selection(
        selection=[('factura', _('Factura')),
                   ('nota_debito_factura', _('Nota Debito Factura')),
                   ('documento_soporte', _('Documento Soporte')),],
        string=_('Tipo de documento'), 
        default='factura'
    )
    password = fields.Char('password')
    general_factura = fields.Many2one('base_electronicos.tabla', string='Asignar a',ondelete='restrict', index=True)
    proveedor_tecnologico = fields.Selection(
        [('Navegasoft', 'Navegasoft'),
         ('Facturatech', 'Facturatech'),
         ('Dataico', 'Dataico'),
         ('Afacturar', 'Afacturar'),
         ('Pagopass', 'Pagopass'),
         ('Propio', 'Propio'),
         ('Otro', 'Otro'),],
        default='Navegasoft',
        string='Proveedor Técnologico',
        help="Con quien se envia el documento electronico."
    )
    otro_proveedor_tecnologico = fields.Char('Otro Proveedor Tecnologico')
    sub_tipo_documento = fields.Selection([
        ('Factura_Electronica', 'Factura_Electronica'),
        ('Nota_debito', 'Nota_debito'),
        ('Nota_credito', 'Nota_credito'),
        ('Documento_soporte', 'Documento_soporte'),
        ('Pos', 'Pos'),
    ], string='Tipo documento')
    country_id = fields.Many2one('res.country', string='Pais', readonly=True, copy=False, compute='_compute_pais')
    
    is_colombia = fields.Boolean(compute='_compute_is_colombia', default=False)


    @api.depends('country_id')
    def _compute_is_colombia(self):
        for record in self:
            record.is_colombia = record.country_id.code == 'CO'

    @api.depends('country_id')
    def _compute_pais(self):
        for record in self:
            record.country_id = record.company_id.country_id.id

    def documento(self):
        valores = self.env['account.move'].search([('journal_id.id', '=', self.diario.id)])
        response2={}
        # print(self.journal_id[0])
        for docu in valores: 
            #documento = valores.general_factura.search([('diario', '=', docu.journal_id[0].id)])
            # print(documento)
            # if documento:
            if docu.move_type == "out_invoice" and self.tipo_factura == "factura":
                docu.tipo_documento = self.tipo_factura
            elif docu.move_type == "out_refund" and self.tipo_factura == "factura":
                docu.tipo_documento = "Nota Credito"
            else:
                docu.tipo_documento = self.tipo_factura

    # def documento(self):
    #     valores = self.env['account.move'].search([('journal_id.id', '=', self.diario.id)])
    #     response2={}
    #     # print(self.journal_id[0])
    #     for docu in valores: 
    #         #documento = valores.general_factura.search([('diario', '=', docu.journal_id[0].id)])
    #         # print(documento)
    #         # if documento:
    #         docu.tipo_documento = self.tipo_factura

class base_electronicos(models.Model):
    _name = 'base_electronicos.tabla'
    _inherit = 'base_electronicos.tabla'

    general_factura = fields.One2many('electronicos_factura.datos_generales','general_factura', ondelete='cascade')
    sub_tipo_documento = fields.Selection([
        ('Factura_Electronica', 'Factura_Electronica'),
        ('Nota_debito', 'Nota_debito'),
        ('Nota_credito', 'Nota_credito'),
        ('Documento_soporte', 'Documento_soporte'),
        ('Pos', 'Pos'),
    ], string='Sub Tipo documento')

class partner_fact(models.Model):
    # _name = 'res.partner'
    _inherit = 'res.partner'

    #vat = fields.Char('Numero de documento')
    first_name = fields.Char(
        string="First Name",
    )
    middle_name = fields.Char(
        string="Middle Name",
    )
    last_name = fields.Char(
        string="Last Name",
    )
    second_last_name = fields.Char(
        string="Second Last Name",
    )
    tipo_contribuyente = fields.Char('Tipo de Contribuyente')
    tipo_documento_plataforma = fields.Char('Tipo de documento')
    numero_plataforma = fields.Char('Documento Numero')
    dv_plataforma= fields.Char('Digito Verificacion')

    correo_factura = fields.Char("Correo Facturación Electrónica")
    tipo_pago = fields.Selection(    
        selection=[#('1', '1 - Instrumento no definido'),
                   ('2', '2 - Crédito ACH'),
                   ('3', '3 - Débito ACH'),
                   ('4', '4 - Reversión débito de demanda ACH'), 
                   ('5', '5 - Reversión crédito de demanda ACH'),
                   ('6', '6 - Crédito de demanda ACH'), 
                   ('7', '7 - Débito de demanda ACH'), 
                   ('8', '8 - Mantener'), 
                   ('9', '9 - Clearing Nacional o Regional'), 
                   ('10', '10 - Efectivo'), 
                   ('11', '11 - Reversión Crédito Ahorro'), 
                   ('12', '12 - Reversión Débito Ahorro'), 
                   ('13', '13 - Crédito Ahorro'), 
                   ('14', '14 - Débito Ahorro'), 
                   ('15', '15 - Bookentry Crédito'), 
                   ('16', '16 - Bookentry Débito'), 
                   ('17', '17 - Concentración de la demanda en efectivo /Desembolso Crédito (CCD)'), 
                   ('18', '18 - Concentración de la demanda en efectivo / Desembolso (CCD) débito'),
                   ('19', '19 - Crédito Pago negocio corporativo (CTP)'), 
                   ('20', '20 - Cheque'), 
                   ('21', '21 - Poyecto bancario'), 
                   ('22', '22 - Proyecto bancario certificado'), 
                   ('23', '23 - Cheque bancario'), 
                   ('24', '24 - Nota cambiaria esperando aceptación'), 
                   ('25', '25 - Cheque certificado'), 
                   ('26', '26 - Cheque Local'), 
                   ('27', '27 - Débito Pago Neogcio Corporativo (CTP)'), 
                   ('28', '28 - Crédito Negocio Intercambio Corporativo (CTX)'), 
                   ('29', '29 - Débito Negocio Intercambio Corporativo (CTX)'), 
                   ('30', '30 - Transferecia Crédito'), 
                   ('42', '42 - Consignación bancaria'), 
                   ('ZZZ', 'ZZZ - Acuerdo mutuo'),],
        string=_('Tipo de pago'), default='10'
    )
    metodo_pago = fields.Selection(
        selection=[('1', _('Contado')),
				   ('2', _('Credito')),],
        string=_('Método de pago'), 
        default='1'
    )
    tipo_factura = fields.Selection(
        selection=[('1', _('1- Combustibles')),
                   ('2', _('2- Emisor es Autorretenedor')),
                   ('3', _('3- Excluidos y Exentos')),
                   ('4', _('4- Extranjero')),
                   ('5', _('5- Generica')),
                   ('6', _('6- Generica con pago anticipado')),
                   ('7', _('7- Generica con periodo de facturacion')),
                   ('8', _('8- Con    sorcio')),
                   ('9', _('9- Servicios AIU')),
                   ('10', _('10- Estandar')),],
        string=_('Tipo de factura'),
        default ='10'
    )
