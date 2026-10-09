from odoo import models, fields, api


class Company(models.Model):
    _inherit = "res.company"

    # ============================================================
    # Datos fiscales
    # ============================================================
    var = fields.Char(related='partner_id.vat', string="TIN")
    verification_code = fields.Char(
        compute='_compute_verification_codes',
        store=True,
        string='VC',
        help='Redundancy check to verify the vat number has been typed in correctly.'
    )

    # ============================================================
    # Parametrización de certificados (POR COMPAÑÍA)
    # - Solo afecta certificados (no toca portal)
    # ============================================================

    # Firmante / responsable
    payroll_manager_id = fields.Many2one(
        'hr.employee',
        string='Payroll Manager (Certificates)',
        help='Empleado responsable/firmante que aparece en certificados.'
    )

    # Logo principal (se usa en /company_logo/<id> que ya existe en el módulo)
    company_logo = fields.Binary(
        string='Company Logo (Certificates)',
        attachment=True,
        help='Logo principal para certificados.'
    )

    # Segundo logo (por defecto se mantiene el estático campoalto.png)
    certificate_logo_2 = fields.Binary(
        string='Logo secundario (Certificates)',
        attachment=True,
        help='Logo secundario opcional para certificados. Si no se configura, se usa el logo estático del módulo.'
    )
    certificate_logo_2_name = fields.Char(string='Nombre logo secundario')

    # Texto/HTML del pie
    certificate_company_info = fields.Html(
        string='Texto pie de página (Certificados)',
        sanitize=False,
        help='Texto/HTML que se imprime en el pie de los certificados.'
    )

    # Textos parametrizables (títulos)
    cert_laboral_title_1 = fields.Char(string='Título 1 (Certificado Laboral)')
    cert_laboral_title_2 = fields.Char(string='Título 2 (Certificado Laboral)')
    cert_functions_title_1 = fields.Char(string='Título 1 (Certificado Funciones)')
    cert_functions_title_2 = fields.Char(string='Título 2 (Certificado Funciones)')

    # Cierre y ciudad
    cert_closing_text = fields.Char(string='Texto de cierre', default='Cordialmente,')
    cert_city = fields.Char(string='Ciudad de expedición')

    # Bloque de firma opcional
    cert_signature_block_html = fields.Html(
        string='Bloque de firma (HTML) - opcional',
        sanitize=False,
        help='Si se llena, este HTML reemplaza el bloque estándar de firma en certificados.'
    )

    # Logos extra para certificado de retenciones (DIAN / MUISCAS)
    iw_logo_left = fields.Binary(string='Logo Izquierdo (Retenciones)', attachment=True)
    iw_logo_left_name = fields.Char(string='Nombre logo izq (Retenciones)')
    iw_logo_right = fields.Binary(string='Logo Derecho (Retenciones)', attachment=True)
    iw_logo_right_name = fields.Char(string='Nombre logo der (Retenciones)')

    # ============================================================
    # Cálculo código verificación NIT
    # ============================================================
    @api.depends('vat')
    def _compute_verification_codes(self):
        for company in self:
            multiplication_factors = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]

            if company.var and company.var != '':
                if len(company.var) <= len(multiplication_factors):
                    number = 0
                    padded_vat = company.vat or ''

                    while len(padded_vat) < len(multiplication_factors):
                        padded_vat = '0' + padded_vat

                    try:
                        for index, vat_number in enumerate(padded_vat):
                            number += int(vat_number) * multiplication_factors[index]

                        number %= 11

                        if number < 2:
                            company.verification_code = str(number)
                        else:
                            company.verification_code = str(11 - number)
                    except ValueError:
                        company.verification_code = ' '
            else:
                company.verification_code = ' '
