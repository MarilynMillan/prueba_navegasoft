# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class centrodecostos(models.Model):
    _name = 'hr.centrocostos'
    _description = 'centros de costos'

    name = fields.Char(string="Centro de costos")
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    departamentos = fields.Many2many("hr.department", string="Centro de costos")
    # cuenta_debito = fields.Many2one("account.account", string="Cuenta debito")
    # cuenta_credito = fields.Many2one("account.account", string="Cuenta crédito")


