# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Attendee(models.Model):
    _inherit = "calendar.attendee"
