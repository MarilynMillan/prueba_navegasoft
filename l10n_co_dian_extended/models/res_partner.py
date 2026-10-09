from lxml import etree

from odoo import api, fields, models
from .. import xml_utils_extend


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_co_dian_update_data(self, company):
        """Override to prevent updating the email from DIAN GetAcquirer."""
        self.ensure_one()
        data = self._l10n_co_dian_call_get_acquirer({
            'identification_type': self._l10n_co_edi_get_carvajal_code_for_identification_type(),
            'identification_number': self._get_vat_without_verification_code(),
            'company': company,
        })
        if data and 'email' in data:
            data.pop('email')
        if data:
            self.write(data)

    @api.model
    def _l10n_co_dian_call_get_acquirer(self, data: dict):
        """Override to use the extended SOAP utilities for GetAcquirer."""
        if not self.env.ref('l10n_co_dian_extended.get_acquirer', raise_if_not_found=False):
            return dict()

        response = xml_utils_extend._build_and_send_request(
            self,
            payload={
                'identification_type': data['identification_type'],
                'identification_number': data['identification_number'],
                'soap_body_template': "l10n_co_dian_extended.get_acquirer",
            },
            service='GetAcquirer',
            company=data['company'],
        )

        if response['status_code'] != 200:
            return dict()

        root = etree.fromstring(response['response'])
        return {
            'email': root.findtext('.//{*}ReceiverEmail'),
            'name': root.findtext('.//{*}ReceiverName'),
        }
