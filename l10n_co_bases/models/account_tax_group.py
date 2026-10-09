# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    code = fields.Char(string="Identifier")
    description = fields.Char(string="Description")
    is_percent = fields.Boolean(string="Is percent", default=True)
