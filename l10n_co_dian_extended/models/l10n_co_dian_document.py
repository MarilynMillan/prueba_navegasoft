from base64 import b64encode, b64decode
from datetime import datetime, timezone
from lxml import etree
from lxml.etree import CDATA

from odoo import api, fields, models, modules
from odoo.tools import cleanup_xml_node
from odoo.addons.l10n_co_dian_extended import xml_utils_extend
from odoo.exceptions import UserError

EVENT_FILE_SEQUENCE_CODE = "l10n_co_dian_file_sequence_code"

COMMERCIAL_STATE_SELECTION = [
    ('pending', "Pendiente"),
    ('received', "030 - Acuse de Recibo"),
    ('goods_received', "032 - Bienes Recibidos"),
    ('claimed', "031 - Reclamada"),
    ('accepted', "033 - Aceptada"),
    ('accepted_by_issuer', "034 - Aceptación Tácita"),
]


class L10nCoDianDocument(models.Model):
    _inherit = 'l10n_co_dian.document'

    commercial_state = fields.Selection(
        selection=COMMERCIAL_STATE_SELECTION,
        string="Estado Comercial",
    )

    show_button_fetch_attached_document = fields.Boolean(
        compute='_compute_show_button_fetch_attached_document',
    )

    @api.depends('attachment_id', 'move_id.move_type')
    def _compute_show_button_fetch_attached_document(self):
        for doc in self:
            doc.show_button_fetch_attached_document = (
                doc.attachment_id and doc.move_id.move_type not in ('in_invoice', 'in_refund')
            )

    # -------------------------------------------------------------------------
    # Override _create_document to support attachment_name and commercial_state
    # -------------------------------------------------------------------------

    @api.model
    def _create_document(self, xml, move, state, **kwargs):
        """
        Override to support:
        - attachment_name: custom filename for the attachment
        - commercial_state: initial commercial state for accepted documents
        - datetime: override signing datetime
        - identifier: override UUID
        """
        move.ensure_one()

        root = etree.fromstring(xml)
        demo_mode = move.company_id.l10n_co_dian_demo_mode

        attachment_name = kwargs.pop('attachment_name', None) or self.env[
            'account.edi.xml.ubl_dian']._export_invoice_filename(move)

        if demo_mode:
            doc_datetime = datetime.now()
        elif 'datetime' in kwargs:
            doc_datetime = kwargs.pop('datetime')
        else:
            # naive local colombian datetime
            signing_time = root.find('.//{*}SigningTime').text
            doc_datetime = (
                datetime.fromisoformat(signing_time)
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        if demo_mode:
            identifier = 'DEMO'
        elif 'identifier' in kwargs:
            identifier = kwargs.pop('identifier')
        else:
            identifier = root.find('.//{*}UUID').text

        # create document
        doc = self.create([{
            'move_id': move.id,
            'identifier': identifier,
            'state': state,
            'datetime': doc_datetime,
            'test_environment': move.company_id.l10n_co_dian_test_environment,
            'certification_process': move.company_id.l10n_co_dian_certification_process,
            **kwargs,
        }])

        if state == 'invoice_accepted' and not doc.commercial_state:
            doc.commercial_state = 'pending'

        # create attachment
        raw_content = xml if isinstance(xml, bytes) else xml.encode()
        doc.attachment_id = self.env['ir.attachment'].create([{
            'raw': raw_content,
            'name': attachment_name,
            'res_id': doc.id if state != 'invoice_accepted' else move.id,
            'res_model': doc._name if state != 'invoice_accepted' else move._name,
        }])

        return doc

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _document_already_processed(self, response_element):
        """
        Checks if a DIAN response indicates a document has already been processed.
        DIAN returns error code 99 with 'Regla: 90' for duplicate invoice submissions,
        or 'Regla: LGC01' for duplicate commercial event submissions.
        """
        is_valid = response_element.findtext('.//{*}IsValid') == 'true'
        response_status_code = response_element.findtext('.//{*}StatusCode')

        if not is_valid and response_status_code == '99':
            errors = response_element.findall(".//{*}ErrorMessage/{*}string")
            if len(errors) == 1:
                error_text = errors[0].text or ''
                if ('Regla: 90' in error_text or 'Regla: LGC01' in error_text):
                    return True

        return False

    # -------------------------------------------------------------------------
    # New DIAN services for commercial events
    # -------------------------------------------------------------------------

    @api.model
    def _send_event_update_status(self, zipped_content, move, next_commercial_state):
        """Send a commercial event (ApplicationResponse) to DIAN via SendEventUpdateStatus."""
        if move.company_id.l10n_co_dian_demo_mode:
            return {
                'state': 'invoice_accepted',
                'commercial_state': next_commercial_state,
                'message_json': {'status': self.env._("Demo mode response")},
            }, dict()

        response = xml_utils_extend._build_and_send_request(
            self,
            payload={
                'content_file': b64encode(zipped_content).decode(),
                'soap_body_template': "l10n_co_dian_extended.send_event_update_status",
            },
            service="SendEventUpdateStatus",
            company=move.company_id,
        )

        if not response['response']:
            return {
                'state': 'invoice_sending_failed',
                'message_json': {'status': self.env._("The DIAN server did not respond.")},
            }, None

        root = etree.fromstring(response['response'])
        state = 'invoice_rejected'

        if response['status_code'] != 200:
            state = 'invoice_sending_failed'
        elif root.findtext('.//{*}IsValid') == 'true':
            state = 'invoice_accepted'

        document_vals = {
            'state': state,
            'commercial_state': next_commercial_state,
            'message_json': self._build_message(root),
        }

        if self._document_already_processed(root):
            # DIAN already accepted this commercial state, force accepted so the flow can continue
            document_vals['state'] = 'invoice_accepted'

        return document_vals, response

    @api.model
    def _get_status_event(self, company_id, track_id):
        """Fetch the status of a commercial event from DIAN via GetStatusEvent."""
        response = xml_utils_extend._build_and_send_request(
            self,
            payload={
                'track_id': track_id,
                'soap_body_template': "l10n_co_dian_extended.get_status_event",
            },
            service="GetStatusEvent",
            company=company_id,
        )

        if not response['response']:
            return {
                'state': 'invoice_sending_failed',
                'message_json': {'status': self.env._("The DIAN server did not respond.")},
            }, None

        root = etree.fromstring(response['response'])
        state = 'invoice_rejected'

        if response['status_code'] != 200:
            state = 'invoice_sending_failed'
        elif root.findtext('.//{*}IsValid') == 'true':
            state = 'invoice_accepted'

        return {
            'state': state,
            'message_json': self._build_message(root),
        }, response

    @api.model
    def _send_commercial_event(self, move, commercial_state_next):
        """
        Orchestrates the full commercial event flow:
        1. Generate the ApplicationResponse XML
        2. Zip and send to DIAN
        3. Create a document record
        4. Build and store the AttachedDocument (invoice + all events)
        """
        locked_move = move.try_lock_for_update()
        if not locked_move:
            return self.env['l10n_co_dian.document']

        xml, errors = self.env['account.edi.xml.ubl_dian']._export_co_send_event_update_status_invoice(
            locked_move, commercial_state_next)
        if errors:
            raise UserError(self.env._("Error(s) while generating the UBL file:\n- %s", '\n- '.join(errors)))

        locked_move.l10n_co_dian_document_ids.filtered(lambda doc: doc.state == 'invoice_rejected').unlink()

        filename = locked_move._l10n_co_dian_get_commercial_event_document_filename('zip')
        zipped_content = xml_utils_extend._zip_xml(filename, xml)

        document_vals, response = self._send_event_update_status(zipped_content, locked_move, commercial_state_next)
        document = self._create_document(xml, move, **document_vals)

        if document.state != 'invoice_accepted':
            # Sending failed - reset the filename sequence to avoid gaps
            sequence = self.env['ir.sequence'].sudo().search(
                [('code', '=', EVENT_FILE_SEQUENCE_CODE), ('company_id', '=', move.company_id.id)])
            if sequence:
                sequence.sudo().number_next = sequence.number_next - 1
            return document

        attached_document_xml, error = move.l10n_co_dian_document_ids._get_attached_document(
            status_response=response)
        if error:
            raise UserError(error)

        attached_document = self.env['ir.attachment'].create([{
            'raw': attached_document_xml,
            'name': f"{filename}.xml",
            'res_model': 'l10n_co_dian.document',
            'res_id': document.id,
        }])

        attached_document_zip = self.env['ir.attachment'].create([{
            'name': f"{filename}.zip",
            'raw': attached_document._build_zip_from_attachments(),
            'res_model': 'l10n_co_dian.document',
            'res_id': document.id,
        }])

        attached_document.unlink()  # was only necessary to build the zip file
        document.attachment_id.unlink()  # _create_document sets the attachment_id to the sent xml file

        document.attachment_id = attached_document_zip
        if not modules.module.current_test:
            self.env.cr.commit()
        return document

    @api.model
    def _send_get_status_event(self, move, track_id):
        """Fetch the current commercial event status for a move and create a document record."""
        if move.company_id.l10n_co_dian_demo_mode:
            return

        document_vals, response = self._get_status_event(move.company_id, track_id)
        if not response:
            raise UserError('\n- '.join(document_vals['message_json'].get('errors', [])))

        date_time = datetime.now()
        document = self._create_document(
            response['response'], move, identifier=track_id, datetime=date_time, **document_vals)
        if document.state != 'invoice_accepted':
            return

        document_xml = b64decode(etree.fromstring(response['response']).findtext('.//{*}XmlBase64Bytes'))

        # Get the commercial state from the response code
        root = etree.fromstring(document_xml)
        last_response = root.findall('.//{*}DocumentResponse')[-1]
        commercial_status_code = last_response.findtext('./{*}Response/{*}ResponseCode')

        document.attachment_id.raw = document_xml

        commercial_states = self.env['account.move']._fields['l10n_co_dian_commercial_state']._description_selection(
            self.env)
        commercial_state = next(
            (k for k, v in commercial_states if v.split(' - ', 1)[0] == commercial_status_code),
            None,
        )
        if commercial_state:
            document.commercial_state = commercial_state

    # -------------------------------------------------------------------------
    # Override _send_bill_sync: improved duplicate detection via GetXmlByDocumentKey
    # (Odoo 19 adds validation that the document in DIAN belongs to this specific move)
    # -------------------------------------------------------------------------

    @api.model
    def _send_bill_sync(self, zipped_content, move):
        """
        Override to add validation when DIAN returns 'Regla: 90' (document already processed).
        Odoo 18 base accepts duplicates directly; Odoo 19 validates by fetching the original
        XML and checking customer name, issue date and issue time match.
        """
        document_vals = super()._send_bill_sync(zipped_content, move)

        # If super already resolved the duplicate (state=invoice_accepted with identifier),
        # apply the extra Odoo-19-style validation before accepting
        if (
            document_vals.get('state') == 'invoice_accepted'
            and document_vals.get('identifier')
            and not document_vals.get('_validated_by_extended', False)
        ):
            identifier = document_vals['identifier']
            # Only run extra validation if we got here due to duplicate detection
            # (super sets identifier from XmlDocumentKey when Regla-90 is returned)
            # Fetch the actual XML from DIAN and verify it matches this move
            xml = self._get_xml_by_document_key(identifier, move)
            if xml:
                xml_element = etree.fromstring(xml)
                xml_customer_name = xml_element.findtext(
                    './/{*}AccountingCustomerParty/{*}Party/{*}PartyName/{*}Name')
                xml_issue_date = xml_element.findtext('./{*}IssueDate')
                xml_issue_time = xml_element.findtext('./{*}IssueTime')

                customer_name = move.partner_id.name
                issue_date = move.l10n_co_dian_post_time.date().isoformat() if move.l10n_co_dian_post_time else None
                issue_time = move.l10n_co_dian_post_time.strftime("%H:%M:%S-05:00") if move.l10n_co_dian_post_time else None

                if not (xml_customer_name == customer_name
                        and xml_issue_date == issue_date
                        and xml_issue_time == issue_time):
                    # Data doesn't match - revert to rejected to avoid accepting wrong document
                    document_vals['state'] = 'invoice_rejected'
                    document_vals.pop('identifier', None)

        return document_vals

    @api.model
    def _get_xml_by_document_key(self, identifier, move):
        """Fetch the original invoice XML from DIAN by CUFE/identifier.
        Used to validate duplicate detection in _send_bill_sync.
        Returns bytes or False if not available.
        """
        if not self.env.ref('l10n_co_dian_extended.get_xml_by_document_key',
                            raise_if_not_found=False):
            return False

        response = xml_utils_extend._build_and_send_request(
            self,
            payload={
                'track_id': identifier,
                'soap_body_template': "l10n_co_dian_extended.get_xml_by_document_key",
            },
            service="GetXmlByDocumentKey",
            company=move.company_id,
        )
        if response['status_code'] == 200:
            root = etree.fromstring(response['response'])
            response_code = root.findtext('.//{*}Code')
            if response_code == '100':
                return b64decode(root.findtext('.//{*}XmlBytesBase64'))
        return False

    def action_get_attached_document(self):
        """Download the AttachedDocument (invoice + events) for this EDI document record."""
        self.ensure_one()
        attached_document, error = self._get_attached_document()
        if error:
            from odoo.exceptions import UserError
            raise UserError(error)
        attachment = self.env['ir.attachment'].create({
            'raw': attached_document,
            'name': self.move_id._l10n_co_dian_get_attached_document_filename() + '_manual.xml',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
        }

    # -------------------------------------------------------------------------
    # Override _get_attached_document to support commercial events
    # -------------------------------------------------------------------------

    def _get_response_history(self, current_response=None):
        """
        Build a list of all ApplicationResponse XMLs for the documents in self,
        from oldest event to newest (current).

        The first document (oldest) is always the dummy 'pending' document and is excluded.
        The last document (newest) is the current event whose response we already have.
        Intermediate documents have their event XML stored in their AttachedDocument zip.
        """
        if self.mapped('move_id')[:1].company_id.l10n_co_dian_demo_mode:
            return [b'<ApplicationResponse></ApplicationResponse>']

        if not current_response:
            # For non-commercial-event case: call GetStatus to get the ApplicationResponse
            current_response = self[-1]._get_status()
            if current_response['status_code'] != 200:
                return "", self.env._(
                    "Error %(code)s when calling the DIAN server: %(response)s",
                    code=current_response['status_code'],
                    response=current_response['response'],
                )

        current_response_etree = etree.fromstring(current_response['response'])
        current_response_raw = b64decode(current_response_etree.findtext(".//{*}XmlBase64Bytes"))
        history = [current_response_raw]

        # sorted()[0] = newest (current event, already in history)
        # sorted()[-1] = oldest (dummy 'pending' document, excluded)
        # sorted()[1:-1] = intermediate events already sent
        for document in self.sorted()[1:-1]:
            if not document.attachment_id or not document.attachment_id.raw:
                continue
            try:
                # The intermediate document's attachment is a ZIP with the AttachedDocument
                attached_document = etree.fromstring(xml_utils_extend._unzip(document.attachment_id.raw))
                document_line_refs = attached_document.findall('./{*}ParentDocumentLineReference')
                if document_line_refs:
                    document_event_xml = document_line_refs[-1].findtext('.//{*}Description')
                    if document_event_xml:
                        history.append(document_event_xml.encode())
            except Exception:
                pass  # If we can't extract the event XML, skip this document

        return history

    def _get_attached_document_values_ext(self, original_xml_etree, response_history):
        """Build template values for the AttachedDocument with multiple parent_documents."""
        move = self.mapped('move_id')[:1]
        identifier_type = move.l10n_co_dian_identifier_type or 'cufe'

        values = {
            'profile_execution_id': original_xml_etree.findtext('./{*}ProfileExecutionID'),
            'id': original_xml_etree.findtext('./{*}ID'),
            'uuid': self[-1].identifier,
            'uuid_attrs': {
                'schemeName': identifier_type.upper() + "-SHA384",
            },
            'issue_date': original_xml_etree.findtext('./{*}IssueDate'),
            'issue_time': original_xml_etree.findtext('./{*}IssueTime'),
            'document_type': "Contenedor de Factura Electrónica",
            'parent_document_id': original_xml_etree.findtext('./{*}ID'),
            'parent_documents': [],
        }

        for idx, event_xml in enumerate(response_history, start=1):
            event_tree = etree.fromstring(event_xml)
            values['parent_documents'].append({
                'id': idx,
                'uuid': self.sorted()[idx - 1].identifier if len(self) >= idx else '',
                'uuid_attrs': {
                    'schemeName': identifier_type.upper() + "-SHA384",
                },
                'issue_date': event_tree.findtext('./{*}IssueDate'),
                'issue_time': event_tree.findtext('./{*}IssueTime'),
                'response_code': event_tree.findtext('.//{*}Response/{*}ResponseCode'),
                'validation_date': event_tree.findtext('./{*}IssueDate'),
                'validation_time': event_tree.findtext('./{*}IssueTime'),
            })

        return values

    def _get_attached_document(self, status_response=None):
        """
        Override to support the commercial event flow with multiple ApplicationResponse XMLs.

        When status_response is provided (commercial event case):
            - Build response_history from all events
            - Render using l10n_co_dian_extended.attached_document template with parent_documents list

        When status_response is None (simple invoice case):
            - Delegate to the base Odoo 18 implementation (single event)
            - For vendor bills: fix supplier/customer node lookup (base assumes AccountingSupplierParty)
        """
        if status_response is None:
            # Replicate base _get_attached_document but with fallback for vendor bill XMLs
            # that use SenderParty/ReceiverParty instead of AccountingSupplierParty/AccountingCustomerParty
            self.ensure_one()
            original_xml_etree = etree.fromstring(self.attachment_id.raw)

            if self.move_id.company_id.l10n_co_dian_demo_mode:
                application_response = b''
                vals = self._demo_get_attached_document_values(original_xml_etree=original_xml_etree)
            else:
                status_resp = self._get_status()
                if status_resp['status_code'] != 200:
                    return "", self.env._(
                        "Error %(code)s when calling the DIAN server: %(response)s",
                        code=status_resp['status_code'],
                        response=status_resp['response'],
                    )
                status_etree = etree.fromstring(status_resp['response'])
                application_response = b64decode(status_etree.findtext(".//{*}XmlBase64Bytes"))
                original_xml_etree = etree.fromstring(self.attachment_id.raw)
                vals = self._get_attached_document_values(
                    original_xml_etree=original_xml_etree,
                    application_response_etree=etree.fromstring(application_response),
                )

            attached_document = self.env['ir.qweb']._render('l10n_co_dian.attached_document', vals)
            attached_doc_etree = etree.fromstring(attached_document)

            # Copy Sender and Receiver with fallback for vendor bill XML structure
            supplier_node = original_xml_etree.find('./{*}AccountingSupplierParty//{*}PartyTaxScheme')
            if supplier_node is None:
                supplier_node = original_xml_etree.find('./{*}SenderParty//{*}PartyTaxScheme')
            customer_node = original_xml_etree.find('./{*}AccountingCustomerParty//{*}PartyTaxScheme')
            if customer_node is None:
                customer_node = original_xml_etree.find('./{*}ReceiverParty//{*}PartyTaxScheme')

            sender_party = attached_doc_etree.find('./{*}SenderParty')
            receiver_party = attached_doc_etree.find('./{*}ReceiverParty')
            if supplier_node is not None and sender_party is not None:
                sender_party.append(supplier_node)
            if customer_node is not None and receiver_party is not None:
                receiver_party.append(customer_node)

            # Add the xmls (enclosed in CDATA)
            desc_node = attached_doc_etree.find('./{*}Attachment/{*}ExternalReference/{*}Description')
            if desc_node is not None:
                desc_node.text = CDATA(self.attachment_id.raw.decode())
            parent_desc = attached_doc_etree.find('./{*}ParentDocumentLineReference//{*}Description')
            if parent_desc is not None:
                parent_desc.text = CDATA(application_response.decode())

            return etree.tostring(cleanup_xml_node(attached_doc_etree), encoding="UTF-8", xml_declaration=True), ""

        # Commercial event flow: build history of all events
        response_history = self._get_response_history(current_response=status_response)
        if isinstance(response_history, tuple):
            return response_history  # (error_msg, error_detail)

        # The oldest document's attachment contains the original invoice XML
        oldest_document = self.sorted()[-1]
        current_attachment_raw = oldest_document.attachment_id.raw
        original_xml_etree = etree.fromstring(current_attachment_raw)

        move = self.mapped('move_id')[:1]
        if move.company_id.l10n_co_dian_demo_mode:
            vals = {
                'profile_execution_id': original_xml_etree.findtext('./{*}ProfileExecutionID'),
                'id': original_xml_etree.findtext('./{*}ID'),
                'uuid': oldest_document.identifier,
                'uuid_attrs': {'schemeName': (move.l10n_co_dian_identifier_type or 'cufe').upper() + "-SHA384"},
                'issue_date': original_xml_etree.findtext('./{*}IssueDate'),
                'issue_time': original_xml_etree.findtext('./{*}IssueTime'),
                'document_type': "Contenedor de Factura Electrónica",
                'parent_document_id': original_xml_etree.findtext('./{*}ID'),
                'parent_documents': [{
                    'id': 1,
                    'uuid': oldest_document.identifier,
                    'uuid_attrs': {'schemeName': (move.l10n_co_dian_identifier_type or 'cufe').upper() + "-SHA384"},
                    'issue_date': 'Demo',
                    'issue_time': 'Demo',
                    'response_code': 'Demo',
                    'validation_date': 'Demo',
                    'validation_time': 'Demo',
                }],
            }
        else:
            vals = self._get_attached_document_values_ext(original_xml_etree, response_history)

        attached_document = self.env['ir.qweb']._render('l10n_co_dian_extended.attached_document', vals)
        attached_doc_etree = etree.fromstring(attached_document)

        # Copy Sender and Receiver from the original invoice XML
        supplier_node = original_xml_etree.find('./{*}AccountingSupplierParty//{*}PartyTaxScheme')
        if supplier_node is None:
            supplier_node = original_xml_etree.find('./{*}SenderParty//{*}PartyTaxScheme')

        customer_node = original_xml_etree.find('./{*}AccountingCustomerParty//{*}PartyTaxScheme')
        if customer_node is None:
            customer_node = original_xml_etree.find('./{*}ReceiverParty//{*}PartyTaxScheme')

        sender_party = attached_doc_etree.find('./{*}SenderParty')
        receiver_party = attached_doc_etree.find('./{*}ReceiverParty')
        if supplier_node is not None and sender_party is not None:
            sender_party.append(supplier_node)
        if customer_node is not None and receiver_party is not None:
            receiver_party.append(customer_node)

        # Add the invoice XML enclosed in CDATA
        description_node = attached_doc_etree.find('./{*}Attachment/{*}ExternalReference/{*}Description')
        if description_node is not None:
            description_node.text = CDATA(current_attachment_raw.decode(encoding='unicode_escape'))

        # Add each event XML enclosed in CDATA in its corresponding ParentDocumentLineReference
        for idx, event_xml in enumerate(response_history, start=1):
            document_element = attached_doc_etree.find(
                f'./{{*}}ParentDocumentLineReference/{{*}}LineID[.="{idx}"]/..')
            if document_element is not None:
                # Roundtrip through etree to remove XML declaration
                try:
                    event_xml_str = etree.tostring(etree.fromstring(event_xml), encoding='unicode')
                except Exception:
                    event_xml_str = event_xml.decode() if isinstance(event_xml, bytes) else event_xml
                event_desc = document_element.find('.//{*}Description')
                if event_desc is not None:
                    event_desc.text = CDATA(event_xml_str)

        return etree.tostring(cleanup_xml_node(attached_doc_etree), encoding="UTF-8", xml_declaration=True), ""
