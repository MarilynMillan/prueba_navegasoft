# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # NOTE: usamos related para que sea MULTI-COMPAÑÍA.

    payroll_manager = fields.Many2one(
        'hr.employee',
        string='Payroll Manager',
        related='company_id.payroll_manager_id',
        readonly=False,
    )

    company_logo = fields.Binary(
        string='Company Logo',
        related='company_id.company_logo',
        readonly=False,
        attachment=True,
    )
    company_logo_name = fields.Char(string='Company Logo Name', readonly=True)

    certificate_logo_2 = fields.Binary(
        string='Logo secundario (Certificates)',
        related='company_id.certificate_logo_2',
        readonly=False,
        attachment=True,
    )
    certificate_logo_2_name = fields.Char(string='Nombre logo secundario', readonly=True)

    certificate_company_info = fields.Html(
        string='Certificate company info',
        related='company_id.certificate_company_info',
        readonly=False,
        sanitize=False,
    )

    cert_laboral_title_1 = fields.Char(related='company_id.cert_laboral_title_1', readonly=False)
    cert_laboral_title_2 = fields.Char(related='company_id.cert_laboral_title_2', readonly=False)
    cert_functions_title_1 = fields.Char(related='company_id.cert_functions_title_1', readonly=False)
    cert_functions_title_2 = fields.Char(related='company_id.cert_functions_title_2', readonly=False)

    cert_closing_text = fields.Char(related='company_id.cert_closing_text', readonly=False)
    cert_city = fields.Char(related='company_id.cert_city', readonly=False)

    cert_signature_block_html = fields.Html(
        related='company_id.cert_signature_block_html',
        readonly=False,
        sanitize=False,
    )

    iw_logo_left = fields.Binary(related='company_id.iw_logo_left', readonly=False, attachment=True)
    iw_logo_left_name = fields.Char(string='Nombre logo izq (Retenciones)', readonly=True)
    iw_logo_right = fields.Binary(related='company_id.iw_logo_right', readonly=False, attachment=True)
    iw_logo_right_name = fields.Char(string='Nombre logo der (Retenciones)', readonly=True)
