
# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware a b
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).a b c d e f g h

from odoo import SUPERUSER_ID, api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    # @api.depends('amount_total')
    # def _compute_amount_total_words(self):
    #     for invoice in self:
    #         invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total).upper()

    # amount_total_words = fields.Char(
    #     string="Total (In Words)",
    #     compute="_compute_amount_total_words" 
    # )
    show_comment = fields.Boolean(
        string="Show Comment",
        default=False,
    )
    invoice_comment = fields.Html(
        string="Invoice Comment"
    )
    # show_invoice_comment = fields.Boolean(string="Show invoice comment", compute="_compute_show_invoice_comment")

    # @api.depends('company_id')
    # def _compute_show_invoice_comment(self):
    #     for record in self:
    #         show_invoice_comment = self.env['ir.config_parameter'].sudo().get_param('l10n_co_bases.comment_text_with_format')
            
    #         if show_invoice_comment == 'True':
    #             record.show_invoice_comment = True
    #         else:
    #             record.show_invoice_comment = False

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_co_line_taxes_print(self):
        self.ensure_one()
        labels = []
        for tax in self.tax_ids:
            if tax.notprintable:
                continue
            label = (
                getattr(tax, "tax_label", False)
                or getattr(tax, "invoice_label", False)
                or tax.name
                or ""
            )
            if label and label not in labels:
                labels.append(label)
        return ", ".join(labels)
