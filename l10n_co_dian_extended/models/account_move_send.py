# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_mail_params(self, move, move_data):
        """Cuando la factura ya fue aceptada por la DIAN y el usuario
        vuelve a enviar el correo, re-adjunta automáticamente el zip
        DIAN (XML AttachedDocument + PDF con CUFE/QR) existente.
        """
        params = super()._get_mail_params(move, move_data)

        if move.l10n_co_dian_state != 'invoice_accepted':
            return params

        zip_name = move._l10n_co_dian_get_attached_document_filename() + '.zip'
        existing_attachments = params.get('attachments') or []
        already_attached = any(att[0] == zip_name for att in existing_attachments)
        if already_attached:
            return params

        zip_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
            ('name', '=', zip_name),
        ], limit=1, order='id desc')

        if zip_attachment:
            params['attachments'] = list(existing_attachments) + [
                (zip_attachment.name, zip_attachment.raw),
            ]
        return params

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        """Expone el zip DIAN ya existente como placeholder en el wizard
        de envío, marcando un id estable para que la UI lo muestre
        preseleccionado cuando la factura ya fue aceptada.
        """
        results = super()._get_placeholder_mail_attachments_data(
            move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis
        )

        if move.l10n_co_dian_state != 'invoice_accepted':
            return results

        zip_name = move._l10n_co_dian_get_attached_document_filename() + '.zip'
        zip_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
            ('name', '=', zip_name),
        ], limit=1, order='id desc')

        if zip_attachment and not any(r.get('name') == zip_name for r in results):
            results = list(results) + [{
                'id': zip_attachment.id,
                'name': zip_name,
                'mimetype': 'application/zip',
            }]
        return results
