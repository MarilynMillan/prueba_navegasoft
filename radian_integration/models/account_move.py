from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    dian_radian_status = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
    ], default='draft', string="Estado RADIAN")

    radian_event_ids = fields.One2many('radian.event.log', 'invoice_id', string="Eventos RADIAN")

    def action_send_radian(self):
        for invoice in self:
            if invoice.move_type != 'out_invoice':
                continue

            payload = invoice._build_radian_payload()
            headers = {
                'Authorization': 'Bearer TU_TOKEN_API',
                'Content-Type': 'application/json'
            }

            url = 'https://api.tu-proveedor.com/radian/register'

            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                self.env['radian.event.log'].create({
                    'invoice_id': invoice.id,
                    'event_type': 'registro',
                    'status': data.get('status'),
                    'response': data.get('message'),
                })

                invoice.dian_radian_status = 'sent' if data.get('status') == 'OK' else 'rejected'

            except Exception as e:
                _logger.error(f"Error al enviar factura a RADIAN: {e}")
                invoice.dian_radian_status = 'rejected'

    def _build_radian_payload(self):
        self.ensure_one()
        return {
            'invoice_number': self.name,
            'customer_vat': self.partner_id.vat,
            'issue_date': str(self.invoice_date),
            'amount_total': self.amount_total,
            'currency': self.currency_id.name,
            'uuid': self.l10n_co_edi_cufe or '',
        }