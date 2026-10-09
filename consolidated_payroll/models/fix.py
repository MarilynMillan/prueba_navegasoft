
from odoo import models, fields, modules,tools , api,_ 
import os
import requests
import json 
from odoo.exceptions import AccessError, UserError,  ValidationError
import babel
from odoo.tools.safe_eval import safe_eval
from functools import partial
import re
import time
from dateutil import relativedelta
from datetime import datetime, timedelta
from datetime import time as datetime_time
import logging
_logger = logging.getLogger(__name__)
from odoo.tools.misc import formatLang
from datetime import datetime as py_datetime
class ResPartner(models.Model):
    _inherit = 'res.partner'

    duplicate_bank_partner_ids=fields.One2many('res.partner.bank', 'partner_id', string='Duplicate Bank Accounts', domain=lambda self: [('partner_id','=',self.id)])
    total_all_due=fields.Float(string='Total All Due', compute='_compute_total_all_due', store=True, readonly=True)
    duplicate_bank_partner_ids = fields.One2many(
        "res.partner.bank", "partner_id", string="Cuentas Bancarias Duplicadas"
    )
    total_all_due = fields.Monetary('')
    total_all_overdue=fields.Monetary('')
    def button_l10n_co_dian_refresh_data(self):
        print("Refrescando datos DIAN...")

    #available_peppol_eas=fields.Boolean(string="Available Peppol EAs")
    has_moves=fields.Boolean(string="Has Moves")
    l10n_co_dian_enable_update_data=fields.Boolean(string="L10n Co Dian Enable Update Data")
    @api.depends('name')
    def _compute_total_all_due(self):
        for rec in self:
            total_due = 0.0
            rec.total_all_due = total_due
class AccountMove(models.Model):
    _inherit = 'account.move'


    expected_currency_rate=fields.Float('')
    account_pick_currency_date=fields.Date('Fecha Tasa de Cambio para Asiento de Inventario')
    account_pick_currency_date=fields.Date('Fecha Tasa de Cambio para Asiento de Inventario')
