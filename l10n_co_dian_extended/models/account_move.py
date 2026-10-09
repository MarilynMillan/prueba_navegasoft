# -*- coding: utf-8 -*-
from pytz import timezone
from lxml import etree

from collections import defaultdict
from datetime import datetime, timedelta
import re

from odoo.api import NewId
from odoo import api, fields, models, modules
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.addons.l10n_co_dian_extended import xml_utils_extend
from odoo.addons.l10n_co_dian_extended.models.l10n_co_dian_document import (
    COMMERCIAL_STATE_SELECTION, EVENT_FILE_SEQUENCE_CODE)
from odoo.tools import (
    partition, Query, SQL,
)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_co_edi_cufe_cude_ref = fields.Char(
        string="CUFE/CUDE/CUDS",
        compute='_compute_l10n_co_dian_cufe',
        store=True,
        readonly=True,
        copy=False,
        help="Unique ID used by the DIAN to identify the invoice.",
    )

    l10n_co_dian_state = fields.Selection(
        selection=[
            ('invoice_sending_failed', "Sending Failed"),
            ('invoice_pending', "Pending"),
            ('invoice_rejected', "Rejected"),
            ('invoice_accepted', "Accepted"),
        ],
        compute='_compute_l10n_co_dian_states',
        store=True,
        copy=False,
    )
    l10n_co_dian_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute='_compute_l10n_co_dian_attachment_id',
    )

    l10n_co_dian_processed_by_get_event_status_cron = fields.Boolean()

    l10n_co_dian_commercial_state = fields.Selection(
        string="Estado Comercial",
        default='pending',
        selection=COMMERCIAL_STATE_SELECTION,
        compute='_compute_l10n_co_dian_states',
        copy=False,
        store=True,
    )

    l10n_co_dian_claim_reason = fields.Selection(
        string="Claim Reason",
        selection=[
            ('01', "Document with inconsistencies"),
            ('02', "Undelivered merchandise"),
            ('03', "Merchandise partially delivered"),
            ('04', "Service not provided"),
        ],
        copy=False,
    )

    l10n_co_dian_update_commercial_event_enabled = fields.Boolean(
        compute='_compute_l10n_co_dian_update_commercial_event_enabled',
    )

    # ----------------------------------------------------------
    # Compute methods
    # ----------------------------------------------------------

    @api.depends(
        'move_type',
        'l10n_co_edi_is_support_document',
        'l10n_co_dian_document_ids.state',
        'l10n_co_dian_document_ids.commercial_state',
    )
    def _compute_l10n_co_dian_cufe(self):
        for move in self:
            if move.move_type in ('in_invoice', 'in_refund') and not move.l10n_co_edi_is_support_document:
                # For vendor bills, preserve whatever was manually set
                move.l10n_co_edi_cufe_cude_ref = move.l10n_co_edi_cufe_cude_ref
                continue

            move.l10n_co_edi_cufe_cude_ref = False
            documents = move.l10n_co_dian_document_ids.sorted()
            is_accepted_by_issuer = False
            for document in documents:
                if document.state not in ('invoice_pending', 'invoice_accepted'):
                    continue

                # For accepted_by_issuer, report the identifier of the first 'pending' document
                if document.commercial_state == 'accepted_by_issuer':
                    is_accepted_by_issuer = True
                if is_accepted_by_issuer and document.commercial_state == 'pending':
                    move.l10n_co_edi_cufe_cude_ref = document.identifier
                    break

                # Otherwise report the identifier of the invoice_accepted document
                if not is_accepted_by_issuer and document.state == 'invoice_accepted':
                    move.l10n_co_edi_cufe_cude_ref = document.identifier
                    break

    @api.depends(
        'l10n_co_dian_document_ids',
        'l10n_co_dian_document_ids.state',
        'l10n_co_dian_document_ids.commercial_state',
    )
    def _compute_l10n_co_dian_states(self):
        for move in self:
            move.l10n_co_dian_commercial_state = False
            move.l10n_co_dian_state = False
            documents = move.l10n_co_dian_document_ids.sorted()
            for document in documents:
                if not move.l10n_co_dian_state:
                    move.l10n_co_dian_state = document.state
                if not move.l10n_co_dian_commercial_state and document.state == 'invoice_accepted':
                    move.l10n_co_dian_commercial_state = document.commercial_state

    @api.depends('l10n_co_dian_document_ids', 'l10n_co_dian_document_ids.state')
    def _compute_l10n_co_dian_attachment_id(self):
        for move in self:
            move.l10n_co_dian_attachment_id = False
            documents = move.l10n_co_dian_document_ids.sorted()
            for document in documents:
                if document.state == 'invoice_accepted':
                    move.l10n_co_dian_attachment_id = document.attachment_id
                    break

    @api.depends('l10n_co_dian_document_ids.state', 'l10n_co_dian_commercial_state')
    def _compute_l10n_co_dian_update_commercial_event_enabled(self):
        for move in self:
            move.l10n_co_dian_update_commercial_event_enabled = (
                any(doc.state == 'invoice_accepted' for doc in move.l10n_co_dian_document_ids)
                and move.l10n_co_dian_commercial_state not in ('claimed', 'accepted', 'accepted_by_issuer')
            )

    # ----------------------------------------------------------
    # Extends methods
    # ----------------------------------------------------------

    def _post(self, soft=True):
        # EXTENDS account
        res = super()._post(soft=soft)
        for move in self.filtered('l10n_co_dian_is_enabled'):
            # naive local Colombian datetime
            now = fields.Datetime.to_string(datetime.now(tz=timezone('America/Bogota')))
            move.l10n_co_dian_post_time = now

            # For vendor bills (not support documents), create a dummy 'pending' document
            # so the commercial event flow (RADIAN) can be initiated
            if move.is_purchase_document() and not move.l10n_co_edi_is_support_document and not move.l10n_co_dian_document_ids:
                self.env['l10n_co_dian.document']._create_document(
                    '<Note>No xml</Note>',
                    move,
                    'invoice_accepted',
                    attachment_name=f'dian_{move.move_type}_{move.name}.xml',
                    commercial_state='pending',
                    message_json={'status': ''},
                    datetime=now,
                    identifier=move.l10n_co_edi_cufe_cude_ref,
                )
        return res

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.l10n_co_dian_state == 'invoice_accepted' and self.l10n_co_dian_attachment_id:
            return 'l10n_co_dian.report_invoice_document'
        elif self.env.ref('l10n_co_dian.report_vendor_document', raise_if_not_found=False) and \
                self.l10n_co_edi_is_support_document and \
                self.move_type in ('in_refund', 'in_invoice'):
            return 'l10n_co_dian.report_vendor_document'
        return super()._get_name_invoice_report()

    # ----------------------------------------------------------
    # Helpers methods
    # ----------------------------------------------------------

    @api.private
    def try_lock_for_update(self, *, allow_referencing: bool = False, limit: int | None = None):
        """ Grab an exclusive write-lock on some rows with the given ids.

        Skip locked records and browse the records that could be locked.

        :param allow_referencing: Acquire a row lock which allows for other
            transactions to reference this record.
        :param limit: The maximum number of rows to lock
        :return: The recordset of locked records
        """
        new_ids, ids = partition(lambda i: isinstance(i, NewId), self._ids)
        if limit is not None:
            if len(new_ids) >= limit:
                return self.browse(new_ids[:limit])
            query = self.browse(ids)._as_query(ordered=True)
            query.limit = limit - len(new_ids)
        else:
            query = Query(self.env, self._table, self._table_sql)
            query.add_where(SQL("%s IN %s", SQL.identifier(self._table, 'id'), tuple(ids)))
        if not ids:
            return self
        if allow_referencing:
            lock_sql = SQL("FOR NO KEY UPDATE SKIP LOCKED")
        else:
            lock_sql = SQL("FOR UPDATE SKIP LOCKED")
        sql = SQL("%s %s", query.select(), lock_sql)
        real_ids = (id_ for [id_] in self.env.execute_query(sql))
        valid_ids = {*real_ids, *new_ids}
        return self.browse(i for i in self._ids if i in valid_ids)

    def _l10n_co_dian_get_extra_invoice_report_values(self):
        """ Get the values used to render the PDF report. """
        self.ensure_one()
        document = self._l10n_co_dian_get_last_accepted_document()
        if not document:
            document = self.l10n_co_dian_document_ids.sorted()[:1]
        return {
            'barcode_src': f'/report/barcode/?barcode_type=QR&value="{self._l10n_co_dian_get_invoice_report_qr_code_value()}"&width=180&height=180&quiet=0',
            'signing_datetime': document.datetime.replace(microsecond=0) if document.datetime else False,
            'identifier': document.identifier,
        }

    def l10n_co_dian_action_update_event_status(self):
        """Fetch latest commercial event status from DIAN and update document records."""
        self.l10n_co_dian_document_ids.filtered(lambda doc: doc.state == 'invoice_rejected').unlink()

        for move in self.try_lock_for_update():
            track_id = move._l10n_co_dian_get_last_accepted_document().identifier
            if not track_id:
                continue

            self.env['l10n_co_dian.document']._send_get_status_event(move, track_id)
            if not modules.module.current_test:
                self.env.cr.commit()

            # Remove duplicate documents per move, keeping only the most recent per commercial_state.
            # Bug previo: usar `self` agrupaba documentos de TODAS las facturas del lote y borraba
            # documentos válidos de otras facturas que compartían commercial_state.
            documents = move.l10n_co_dian_document_ids.sorted()[:-1]
            grouped_documents = documents.grouped(key='commercial_state')
            for commercial_state, duplicate_documents in grouped_documents.items():
                duplicate_documents.sorted()[1:].unlink()

    # ----------------------------------------------------------
    # RADIAN commercial event methods
    # ----------------------------------------------------------

    def l10n_co_dian_send_event_update_status_received(self):
        """Send 030 - Acknowledge Reception event to DIAN."""
        self._l10n_co_dian_send_event_update_status('received')

    def l10n_co_dian_send_event_update_status_claimed(self):
        """Send 031 - Claim event to DIAN (requires l10n_co_dian_claim_reason to be set)."""
        self._l10n_co_dian_send_event_update_status('claimed')

    def l10n_co_dian_send_event_update_status_goods_received(self):
        """Send 032 - Goods/Services Received event to DIAN."""
        self._l10n_co_dian_send_event_update_status('goods_received')

    def l10n_co_dian_send_event_update_status_accepted(self):
        """Send 033 - Accepted by Customer event to DIAN."""
        self._l10n_co_dian_send_event_update_status('accepted')

    def l10n_co_dian_send_event_update_status_accepted_by_issuer(self):
        """Send 034 - Accepted by Issuer (Tacit Acceptance) event to DIAN."""
        self._l10n_co_dian_send_event_update_status('accepted_by_issuer')

    def _l10n_co_dian_send_event_update_status(self, commercial_state_next):
        if not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(self.env._("Only invoicing users can update the DIAN commercial status."))

        self.ensure_one()
        self._l10n_co_dian_validate_send_event_update_data()

        # For older vendor bills that were posted before the module was installed,
        # create the dummy 'pending' document so the RADIAN flow can work
        if self.is_purchase_document() and not self.l10n_co_edi_is_support_document and not self.l10n_co_dian_document_ids:
            now = fields.Datetime.to_string(datetime.now(tz=timezone('America/Bogota')))
            self.env['l10n_co_dian.document']._create_document(
                '<Note>No xml</Note>',
                self,
                'invoice_accepted',
                attachment_name=f'dian_{self.move_type}_{self.name}.xml',
                commercial_state='pending',
                message_json={'status': ''},
                datetime=now,
                identifier=self.l10n_co_edi_cufe_cude_ref,
            )

        # For vendor bills, check if DIAN already has events registered
        # (e.g. processed outside Odoo). If so, sync the state instead of resending.
        if self.is_purchase_document() and self.l10n_co_edi_cufe_cude_ref:
            self._l10n_co_dian_sync_vendor_bill_events()
            # After sync, check if the requested state is already reached
            if self.l10n_co_dian_commercial_state and self.l10n_co_dian_commercial_state != 'pending':
                state_order = {'pending': 0, 'received': 1, 'goods_received': 2, 'claimed': 3, 'accepted': 3, 'accepted_by_issuer': 4}
                current_idx = state_order.get(self.l10n_co_dian_commercial_state, -1)
                next_idx = state_order.get(commercial_state_next, 99)
                if current_idx >= next_idx:
                    return  # Already at or past the requested state

        document = self.env['l10n_co_dian.document']._send_commercial_event(self, commercial_state_next)

        if document.state == 'invoice_accepted':
            # Log event in chatter without sending email notifications
            AccountMoveSend = self.env['account.move.send']
            mail_template = self.env.ref('l10n_co_dian_extended.email_template_commercial_event')
            mail_lang = AccountMoveSend._get_default_mail_lang(self, mail_template)

            self.with_context(
                mail_notify_force_send=False,
                mail_auto_subscribe_no_notify=True,
            ).message_post(
                message_type='notification',
                subtype_id=self.env.ref('mail.mt_note').id,
                body=AccountMoveSend._get_default_mail_body(self, mail_template, mail_lang),
                subject=AccountMoveSend._get_default_mail_subject(self, mail_template, mail_lang),
                attachments=[(self.l10n_co_dian_attachment_id.name, self.l10n_co_dian_attachment_id.raw)]
                if self.l10n_co_dian_attachment_id else [],
            )

    def _l10n_co_dian_validate_send_event_update_data(self):
        """Validate required fields before sending a commercial event."""
        errors = []
        if self.move_type in ('in_invoice', 'in_refund'):
            if not self.ref:
                errors.append(self.env._("The Bill Reference is required to send commercial events."))
            if not self.l10n_co_edi_cufe_cude_ref:
                errors.append(self.env._("The Bill CUFE/CUDE is required to send commercial events."))
            # RADIAN events only apply to credit invoices (PaymentMeansID=2)
            if hasattr(self, 'l10n_co_edi_is_direct_payment') and self.l10n_co_edi_is_direct_payment:
                errors.append(self.env._(
                    "RADIAN commercial events only apply to credit invoices (a crédito). "
                    "This invoice is marked as direct payment (de contado). "
                    "Verify that the payment due date is different from the invoice date."
                ))

        if errors:
            raise ValidationError('\n'.join(errors))

        if self.partner_id and not self.partner_id.vat:
            raise RedirectWarning(
                message=self.env._("The receiving partner's identification number is required to send commercial events."),
                action={
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.partner',
                    'context': {'create': False},
                    'view_mode': 'form',
                    'views': [[self.env.ref('base.view_partner_form').id, 'form']],
                    'res_id': self.partner_id.id,
                },
                button_text=self.env._("Go to Partner"),
            )

    def _l10n_co_dian_sync_vendor_bill_events(self):
        """Sync commercial event status from DIAN for vendor bills using GetStatusEvent.
        Updates the local document records to reflect events already registered in DIAN."""
        self.ensure_one()
        track_id = self.l10n_co_edi_cufe_cude_ref
        if not track_id:
            return

        try:
            self.env['l10n_co_dian.document']._send_get_status_event(self, track_id)
        except (UserError, Exception):
            return  # If DIAN doesn't respond or errors, just continue with normal flow

        # Clean up duplicate documents
        documents = self.l10n_co_dian_document_ids.sorted()[:-1]
        if documents:
            grouped = documents.grouped(key='commercial_state')
            for _state, dupes in grouped.items():
                dupes.sorted()[1:].unlink()

    def _l10n_co_dian_get_mail_commercial_state_label(self):
        """Returns the localized label for the current commercial state."""
        self.ensure_one()
        commercial_states = dict(
            self._fields['l10n_co_dian_commercial_state']._description_selection(
                self.with_context(lang=self.partner_id.lang).env))
        return commercial_states.get(self.l10n_co_dian_commercial_state, '')

    def _l10n_co_dian_get_electronic_document_number(self):
        """Extract the document number (ID) from the DIAN attachment XML."""
        self.ensure_one()
        if not self.l10n_co_dian_attachment_id:
            return None

        raw = self.l10n_co_dian_attachment_id.raw
        try:
            if self.move_type in ('in_invoice', 'in_refund') and not self.l10n_co_edi_is_support_document:
                # Try unzip first (AttachedDocument zip), fall back to raw XML
                try:
                    root = etree.fromstring(xml_utils_extend._unzip(raw))
                except Exception:
                    root = etree.fromstring(raw)
            else:
                root = etree.fromstring(raw)

            nsmap = {k: v for k, v in root.nsmap.items() if k}
            return root.findtext('./cbc:ID', namespaces=nsmap)
        except Exception:
            return None

    def _l10n_co_dian_get_commercial_event_document_filename(self, file_ext):
        """Generate a unique filename for a commercial event document."""
        self.ensure_one()
        prefix = 'ar' if file_ext == 'xml' else 'z'
        vat = self.company_id.partner_id._get_vat_without_verification_code().zfill(10)
        year = fields.Datetime.now().strftime("%y")

        suffix = self.with_company(self.company_id).env['ir.sequence'].sudo().next_by_code(EVENT_FILE_SEQUENCE_CODE)
        if not suffix:
            sequence = self.env['ir.sequence'].sudo().create([{
                'name': f"Commercial Event File Name ({self.company_id.name})",
                'code': EVENT_FILE_SEQUENCE_CODE,
                'company_id': self.company_id.id,
                'implementation': 'no_gap',
                'use_date_range': True,
            }])
            suffix = sequence.sudo().next_by_id()

        return f'{prefix}{vat}000{year}{int(suffix):0{8}X}'

    def _l10n_co_dian_get_last_accepted_document(self):
        """Return the most recent invoice_accepted document for this move."""
        self.ensure_one()
        return next(
            (d for d in self.l10n_co_dian_document_ids.sorted() if d.state == 'invoice_accepted'),
            self.env['l10n_co_dian.document'],
        )

    def l10n_co_dian_regenerate_zip(self):
        """Regenerate the DIAN zip (AttachedDocument XML + PDF with CUFE/QR).

        Use this when the invoice was accepted by DIAN but the zip was not
        generated correctly (e.g. due to a transient error during Send & Print).
        """
        self.ensure_one()
        if self.l10n_co_dian_state != 'invoice_accepted':
            raise UserError(self.env._(
                "Only invoices accepted by the DIAN can have their zip regenerated."
            ))

        doc = self._l10n_co_dian_get_last_accepted_document()
        if not doc or not doc.attachment_id:
            raise UserError(self.env._(
                "No accepted DIAN document found with an XML attachment."
            ))

        # 1. Get AttachedDocument XML from DIAN
        attached_document_xml, error = doc._get_attached_document()
        if error:
            raise UserError(self.env._(
                "Error fetching AttachedDocument from DIAN:\n%(error)s",
                error=error,
            ))

        # 2. Delete the old PDF so it can be regenerated with CUFE/QR data
        if self.invoice_pdf_report_id:
            self.invoice_pdf_report_id.unlink()
            self.invalidate_recordset(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])

        # 3. Regenerate the PDF using the standard invoice report
        #    (the DIAN template is selected automatically by _get_name_invoice_report
        #     during QWeb rendering, not via ir.actions.report)
        pdf_report = self.env.ref('account.account_invoices')
        content, report_type = self.env['ir.actions.report'].with_company(
            self.company_id
        )._pre_render_qweb_pdf(pdf_report.report_name, res_ids=self.ids)
        content_by_id = self.env['ir.actions.report']._get_splitted_report(
            pdf_report.report_name, content, report_type
        )
        pdf_content = content_by_id.get(self.id)
        if not pdf_content:
            raise UserError(self.env._("Failed to generate the PDF report."))

        # 4. Save the new PDF as invoice_pdf_report_file
        pdf_attachment = self.env['ir.attachment'].sudo().create({
            'name': self._get_invoice_report_filename(),
            'raw': pdf_content,
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
            'res_field': 'invoice_pdf_report_file',
        })
        self.message_main_attachment_id = pdf_attachment
        self.invalidate_recordset(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])

        # 5. Build zip: AttachedDocument XML + new PDF
        xml_attachment = self.env['ir.attachment'].create({
            'raw': attached_document_xml,
            'name': self._l10n_co_dian_get_attached_document_filename() + ".xml",
            'res_model': 'account.move',
            'res_id': self.id,
        })
        zip_content = (xml_attachment + self.invoice_pdf_report_id)._build_zip_from_attachments()
        xml_attachment.unlink()

        zip_name = self._l10n_co_dian_get_attached_document_filename() + ".zip"

        # 5.b. Eliminar zips DIAN anteriores adjuntos a esta factura para que
        #      no queden duplicados y el único zip vigente sea el nuevo.
        old_zips = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('name', '=', zip_name),
        ])
        old_zips.unlink()

        zip_attachment = self.env['ir.attachment'].create({
            'name': zip_name,
            'raw': zip_content,
            'res_model': 'account.move',
            'res_id': self.id,
        })

        # 6. Post the zip in the chatter
        self.with_context(no_new_invoice=True).message_post(
            body=self.env._(
                "DIAN zip regenerated with corrected PDF (CUFE/QR included)."
            ),
            attachment_ids=zip_attachment.ids,
        )

    def _l10n_co_dian_cron_update_event_status(self, *, limit=3):
        """
        Cron job: update commercial event status for pending invoices.
        Processes invoices in batches to avoid timeouts.
        """
        date_limit = fields.Datetime.now().date() - timedelta(days=30)

        to_process_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('l10n_co_dian_commercial_state', 'in', ('pending', 'received', 'goods_received')),
            ('l10n_co_edi_cufe_cude_ref', '!=', False),
            ('invoice_date', '>=', date_limit),
            ('l10n_co_dian_processed_by_get_event_status_cron', '=', False),
        ]

        records = self.search(domain=to_process_domain, limit=limit)
        records.l10n_co_dian_action_update_event_status()
        records.l10n_co_dian_processed_by_get_event_status_cron = True

        remaining = self.search_count(domain=to_process_domain)
        if not remaining:
            # Reset the processed flag so the next cycle processes all again
            processed_records = self.search([('l10n_co_dian_processed_by_get_event_status_cron', '=', True)])
            processed_records.l10n_co_dian_processed_by_get_event_status_cron = False
