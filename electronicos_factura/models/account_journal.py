# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    _name = "account.journal"

    code_refund = fields.Char("Code refund") 
    secure_sequence_id = fields.Many2one('ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        check_company=True,
        readonly=False, copy=False)
    invoice_comment = fields.Html(
        string="Invoice Comment"
    )
    number_refund_from = fields.Integer('inicio refund')#, required=True
    number_refund_to = fields.Integer('fin refund')#, required=True
    resolucion_refund = fields.Char('Resolucion refund')
    country_id = fields.Many2one('res.country', string='Pais', readonly=True, copy=False, compute='_compute_pais')
    refund_fecha_desde = fields.Date('Fecha inicio refund')
    refund_fecha_hasta = fields.Date('Fecha fin refund')
    number_refund_to = fields.Integer('fin refund')

    is_colombia = fields.Boolean(compute='_compute_is_colombia', default=False)

    @api.depends('country_id')
    def _compute_is_colombia(self):
        for record in self:
            record.is_colombia = record.country_id.code == 'CO'

    @api.depends('country_id')
    def _compute_pais(self):
        for record in self:
            record.country_id = record.company_id.country_id.id



# class AccountJournal_2(models.Model):
#     _name = "account.journal"
#     _inherit = "account.journal"

   
#     @api.model
#     def create(self, vals):

#         return super(AccountJournal, self).create(vals)

#     @api.model
#     def _create_sequence(self, vals, refund=False):

#         return super(AccountJournal, self)._create_sequence(vals, refund)