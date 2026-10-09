# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_partner(self):
        res_partner = self.env['res.partner'].sudo()
        partner_id = res_partner.browse(1)
        return partner_id.id

    city_id = fields.Many2one('res.city', compute="_compute_address", inverse="_inverse_city_id", string="City of Address")
    vat_vd = fields.Integer(compute="_compute_address", inverse="_inverse_vat_vd", string="Verification digit")
    default_partner_id = fields.Many2one('res.partner', string="Default partner", required=True, default=_get_default_partner)

    default_taxes_ids = fields.Many2many(
        string="Customer taxes",
        comodel_name="account.tax",
        relation="company_default_taxes_rel",
        column1="product_id",
        column2="tax_id",
        domain="[('type_tax_use','=','sale')]",
        help="Taxes applied for sale.",
    )
    default_supplier_taxes_ids = fields.Many2many(
        string="Supplier taxes",
        comodel_name="account.tax",
        relation="company_default_supplier_taxes_rel",
        column1="product_id",
        column2="tax_id",
        domain="[('type_tax_use','=','purchase')]",
        help="Taxes applied for purchase.",
    )

    def _get_company_address_fields(self, partner):
        result = super(ResCompany, self)._get_company_address_fields(partner)
        result['city_id'] = partner.city_id.id
        result['vat_vd'] = partner.vat_vd
        return result

    def _inverse_vat_vd(self):
        for company in self:
            company.partner_id.vat_vd = company.vat_vd
            company.default_partner_id.vat_vd = company.vat_vd


    def _inverse_city_id(self):
        for company in self:
            company.partner_id.city_id = company.city_id
            company.default_partner_id.city_id = company.city_id

    def _inverse_street(self):
        result = super(ResCompany, self)._inverse_street()
        for company in self:
            company.default_partner_id.street = company.street

    def _inverse_country(self):
        result = super(ResCompany, self)._inverse_country()
        for company in self:
            company.default_partner_id.country_id = company.country_id