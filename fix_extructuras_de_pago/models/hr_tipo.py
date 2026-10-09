# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class tipo(models.Model):
    _name = 'hr.tipo'
    _description = 'tipo de administradoras'

    name = fields.Char(string="Administradora")

