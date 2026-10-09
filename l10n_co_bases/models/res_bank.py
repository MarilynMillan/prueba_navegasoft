# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api

class ResBank(models.Model):
    _inherit = 'res.bank'

    city_id = fields.Many2one('res.city', string="City of Address")