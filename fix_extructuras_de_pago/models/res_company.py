# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Company_administradora(models.Model):
    _inherit = "res.company"
    _description = 'admin_compania'

    administradoras_ids = fields.Many2many("hr.administradoras", string="Administradoras",domain="[('compania', '=', True)]")

