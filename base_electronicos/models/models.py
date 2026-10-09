# -*- coding: utf-8 -*-
from odoo import models, fields, api

class base_electronicos(models.Model):
    _name = 'base_electronicos.tabla'
    _description = "tabla para los documentos electronicos"

    name = fields.Char('Nombre')
    tipo_documento = fields.Char(string="Documento")# , compute='documento',store=True
    
    sub_tipo_documento = fields.Selection([
        ('Factura Electronica', 'Factura Electronica'),
        ('Nota_debito', 'Nota_debito'),
        ('Nota_credito', 'Nota_credito'),
        ('Documento_soporte', 'Documento_soporte'),
        ('Pos', 'Pos'),
    ], string='Tipo documento')
    url = fields.Char("URL endpoint",default="https://odoo15.navegasoft.com/admonclientes") #url 
    mp_id = fields.One2many('base_electronicos.line','mp_id') #, ondelete='cascade'


class line_nomina(models.Model):
    _name = 'base_electronicos.line'
    _description = 'base_electronicos.line'

    name = fields.Char('Nombre')
    categoria = fields.Char('Categoria')
    codigo = fields.Char('Codigo')
    dias = fields.Boolean('Son dias?')
    horas = fields.Boolean('Son horas?')
    porcentaje = fields.Boolean('Es porcentaje?')
    subcategoria = fields.Char('Sub Categoria')
    obligatorio = fields.Boolean('Obligatorio')
    detalle = fields.Char('Detalle')
    mensaje = fields.Char('Mensaje')
    campo_tecnico = fields.Char('Campo tecnico')
    titulo = fields.Char('Titulo')
    link = fields.Char('Link')

    mp_id = fields.Many2one('base_electronicos.tabla', string='Campos', index=True) #,ondelete='restrict'