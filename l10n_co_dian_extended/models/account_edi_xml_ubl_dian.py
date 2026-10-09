import logging
import re

from lxml import etree
from hashlib import sha384
from pytz import timezone
from stdnum.co.nit import compact

from datetime import datetime

from odoo import api, models, fields, _
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.l10n_co_dian_extended import xml_utils_extend
from odoo.addons.l10n_co_edi.models.res_partner import FINAL_CONSUMER_VAT
from odoo.addons.l10n_co_edi.models.account_invoice import L10N_CO_EDI_TYPE
from odoo.tools import cleanup_xml_node, frozendict


_logger = logging.getLogger(__name__)


class AccountEdiXmlUbl_Dian(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_dian'

    # -------------------------------------------------------------------------
    # EXPORT: Commercial Events (ApplicationResponse)
    # -------------------------------------------------------------------------

    def _export_co_send_event_update_status_invoice(self, invoice, next_commercial_state):
        """Generate and sign an ApplicationResponse XML for a RADIAN commercial event."""
        vals = {'invoice': invoice, 'l10n_co_dian_commercial_state_next': next_commercial_state}
        document_node = self._get_co_invoice_event_update_status_node(vals)
        document_nsmap = self._get_co_invoice_event_update_status_nsmap(vals)

        xml_content = dict_to_xml(document_node, nsmap=document_nsmap)
        xml = etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8')
        return self.with_context(l10n_co_next_commercial_state=next_commercial_state)._dian_sign_xml(xml, invoice)

    def _get_co_invoice_event_update_status_node(self, vals):
        self._add_co_invoice_event_update_status_config_vals(vals)

        document_node = {'_tag': 'ApplicationResponse'}
        self._add_co_invoice_event_update_status_header_nodes(document_node, vals)
        self._add_co_invoice_event_update_status_note_nodes(document_node, vals)
        self._add_co_invoice_event_update_status_sender_party_nodes(document_node, vals)
        self._add_co_invoice_event_update_status_receiver_party_nodes(document_node, vals)
        self._add_co_invoice_event_update_status_document_response_nodes(document_node, vals)

        document_node['cbc:UUID']['_text'] = self._dian_calculate_cude_sha384(document_node, vals)

        return document_node

    def _add_co_invoice_event_update_status_config_vals(self, vals):
        invoice = vals['invoice']
        vals.update({
            'now': datetime.now(tz=timezone('America/Bogota')),
            'sender_partner': invoice.company_id.partner_id,
            'receiver_partner': invoice.partner_id,
            'is_test_env': invoice.company_id.l10n_co_dian_test_environment,
            'tax_types': invoice.line_ids.tax_ids.flatten_taxes_hierarchy().mapped('l10n_co_edi_type'),
        })

        # For vendor bills, use the cleaned ref directly as the document number.
        # The ref field always contains the correct DIAN document reference.
        if invoice.is_purchase_document():
            vals['dian_doc_number'] = self._clean_dian_document_ref(invoice.ref)

    @api.model
    def _clean_dian_document_ref(self, ref):
        """Remove spaces from document references to match DIAN format.
        E.g. 'FEGM 32044' -> 'FEGM32044' (Serie + Folio without space)."""
        return re.sub(r'\s+', '', ref) if ref else ref

    def _add_co_invoice_event_update_status_header_nodes(self, node, vals):
        invoice = vals['invoice']
        commercial_state_values = invoice._fields['l10n_co_dian_commercial_state'].get_values(self.env)
        if invoice.is_purchase_document():
            id_prefix = (
                vals.get('dian_doc_number')
                or self._clean_dian_document_ref(invoice.ref)
            )
        else:
            id_prefix = invoice.name

        node.update({
            'cbc:UBLVersionID': {'_text': 'UBL 2.1'},
            'cbc:CustomizationID': {'_text': '1'},
            'cbc:ProfileID': {'_text': 'DIAN 2.1: ApplicationResponse de la Factura Electrónica de Venta'},
            'cbc:ProfileExecutionID': {'_text': '2' if vals['is_test_env'] else '1'},
            'cbc:ID': {
                # the move id suffixed by a number that increases with every call
                '_text': f'{id_prefix}{commercial_state_values.index(vals["l10n_co_dian_commercial_state_next"])}',
            },
            'cbc:UUID': {
                'schemeID': '2' if vals['is_test_env'] else '1',
                'schemeName': 'CUDE-SHA384',
            },
            'cbc:IssueDate': {'_text': vals['now'].date().isoformat()},
            'cbc:IssueTime': {'_text': vals['now'].strftime("%H:%M:%S-05:00")},
        })

    def _add_co_invoice_event_update_status_note_nodes(self, node, vals):
        invoice = vals['invoice']
        if invoice.move_type in ('out_invoice', 'out_refund') and vals[
                'l10n_co_dian_commercial_state_next'] == 'accepted_by_issuer':
            last_event_xml = etree.fromstring(invoice.l10n_co_dian_document_ids.sorted()[0].attachment_id.raw)
            last_event_cufe = last_event_xml.findtext('./{*}UUID')
            node.update({
                'cbc:Note': {
                    '_text': (
                        f"Manifiesto bajo la gravedad de juramento que transcurridos 3 días hábiles contados desde "
                        f"la creación del Recibo de bienes y servicios {invoice.name} con CUDE {last_event_cufe}, "
                        f"el adquirente {invoice.partner_id.name} identificado con NIT {invoice.partner_id.vat} "
                        f"no manifestó expresamente la aceptación o rechazo de la referida factura, "
                        f"ni reclamó en contra de su contenido."
                    ),
                }
            })

    def _add_co_invoice_event_update_status_sender_party_nodes(self, node, vals):
        node['cac:SenderParty'] = {
            'cac:PartyTaxScheme': self._get_co_invoice_event_update_status_party_tax_scheme_node(
                {**vals, 'partner': vals['sender_partner'], 'role': 'sender'}),
        }

    def _add_co_invoice_event_update_status_receiver_party_nodes(self, node, vals):
        receiver_partner = vals['receiver_partner']
        node['cac:ReceiverParty'] = {
            'cac:PartyTaxScheme': self._get_co_invoice_event_update_status_party_tax_scheme_node(
                {**vals, 'partner': receiver_partner, 'role': 'receiver'}),
        }

        if vals['l10n_co_dian_commercial_state_next'] != 'accepted_by_issuer':
            node['cac:ReceiverParty']['cac:Contact'] = {
                'cbc:ElectronicMail': {'_text': receiver_partner.email},
            }

    def _get_co_invoice_event_update_status_party_tax_scheme_node(self, vals):
        partner = vals['partner']

        if vals['role'] == 'sender':
            registration_name = partner.display_name
        elif vals['l10n_co_dian_commercial_state_next'] != 'accepted_by_issuer':
            registration_name = partner.name
        else:
            registration_name = "Unidad Administrativa Especial Dirección de Impuestos y Aduanas Nacionales"

        tax_type = vals['tax_types'][0] if vals['tax_types'] else None
        # Default TaxScheme to ZZ/No aplica when no tax types found on invoice lines
        tax_scheme_code = tax_type.code if tax_type else 'ZZ'
        tax_scheme_name = tax_type.name if tax_type else 'No aplica'

        if vals['role'] == 'sender' and vals['l10n_co_dian_commercial_state_next'] == 'accepted_by_issuer':
            partner_vat = '800197268'  # VAT number of DIAN
        else:
            partner_vat = partner._get_vat_without_verification_code()

        return {
            'cbc:RegistrationName': {'_text': registration_name},
            'cbc:CompanyID': {
                '_text': partner_vat,
                'schemeName': partner._l10n_co_edi_get_carvajal_code_for_identification_type(),
                'schemeAgencyName': "CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)",
                'schemeAgencyID': "195",
                'schemeID': partner._get_vat_verification_code(),
                'schemeVersionID': "1",
            },
            'cac:TaxScheme': {
                'cbc:ID': {'_text': tax_scheme_code},
                'cbc:Name': {'_text': tax_scheme_name},
            },
        }

    def _add_co_invoice_event_update_status_document_response_nodes(self, node, vals):
        node['cac:DocumentResponse'] = {
            'cac:Response': self._get_co_invoice_event_update_status_response_node(vals),
            'cac:DocumentReference': self._get_co_invoice_event_update_status_document_reference_node(vals),
        }

        if vals['l10n_co_dian_commercial_state_next'] in ('received', 'goods_received'):
            node['cac:DocumentResponse'][
                'cac:IssuerParty'] = self._get_co_invoice_event_update_status_issuer_party_node(vals)

    def _get_co_invoice_event_update_status_response_node(self, vals):
        invoice = vals['invoice']

        match vals['l10n_co_dian_commercial_state_next']:
            case 'received':
                description = "Acuse de recibo de Factura Electrónica de Venta"
            case 'goods_received':
                description = "Recibo del bien y/o prestación del servicio"
            case 'claimed':
                description = "Reclamo de la Factura Electrónica de Venta"
            case 'accepted':
                description = "Aceptación expresa"
            case 'accepted_by_issuer':
                description = "Aceptación Tácita"
            case unknown_state:
                _logger.warning(_("Unknown commercial state %(state)s", state=unknown_state))
                description = None

        commercial_states = dict(invoice._fields['l10n_co_dian_commercial_state']._description_selection(self.env))

        node = {
            'cbc:ResponseCode': {
                '_text': commercial_states[vals['l10n_co_dian_commercial_state_next']].split(' - ', 1)[0],
            },
            'cbc:Description': {'_text': description},
        }

        if vals['l10n_co_dian_commercial_state_next'] == 'claimed':
            # DIAN expects the claim reason names in Spanish
            claim_reasons = invoice._fields['l10n_co_dian_claim_reason']._description_selection(
                self.with_context(lang='es_419').env)
            node['cbc:ResponseCode'].update({
                'listID': invoice.l10n_co_dian_claim_reason,
                'name': next(v for k, v in claim_reasons if k == invoice.l10n_co_dian_claim_reason),
            })

        return node

    def _get_co_invoice_event_update_status_document_reference_node(self, vals):
        invoice = vals['invoice']

        if invoice.is_purchase_document():
            # Use doc number/type fetched from DIAN XML (via GetXmlByDocumentKey),
            # or fall back to cleaned ref. Do NOT use _l10n_co_dian_get_electronic_document_number()
            # as it may return event document numbers after sync instead of invoice numbers.
            doc_number = vals.get('dian_doc_number') or self._clean_dian_document_ref(invoice.ref)
            doc_type = vals.get('dian_doc_type') or invoice.l10n_co_edi_type or '01'
        else:
            doc_number = invoice.name
            doc_type = invoice.l10n_co_edi_type or '01'

        return {
            'cbc:ID': {'_text': doc_number},
            'cbc:UUID': {
                '_text': invoice.l10n_co_edi_cufe_cude_ref,
                'schemeName': 'CUFE-SHA384',
            },
            'cbc:DocumentTypeCode': {'_text': doc_type.zfill(2)},
        }

    def _get_co_invoice_event_update_status_issuer_party_node(self, vals):
        invoice = vals['invoice']
        partner = invoice.partner_id
        # For vendor bills (purchase), the issuer party person is the company's representative
        if invoice.is_purchase_document():
            company_partner = invoice.company_id.partner_id
            person_name = company_partner.name
            person_vat = compact(company_partner.vat)
            person_id_type = company_partner._l10n_co_edi_get_carvajal_code_for_identification_type()
            person_vat_full = company_partner.vat
            job_title = company_partner.function or 'Representante Legal'
        else:
            person_name = partner.name
            person_vat = compact(partner.vat)
            person_id_type = partner._l10n_co_edi_get_carvajal_code_for_identification_type()
            person_vat_full = partner.vat
            job_title = partner.function or 'Representante Legal'

        return {
            'cac:Person': {
                'cbc:ID': {
                    '_text': person_vat,
                    'schemeName': person_id_type,
                    'schemeID': person_vat_full,
                },
                'cbc:FirstName': {'_text': person_name},
                'cbc:FamilyName': {'_text': person_name},
                'cbc:JobTitle': {'_text': job_title},
                'cbc:OrganizationDepartment': {'_text': job_title},
            }
        }

    def _get_co_invoice_event_update_status_nsmap(self, vals):
        return {
            None: 'urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sts': 'dian:gov:co:facturaelectronica:Structures-2-1',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#',
            'xades141': 'http://uri.etsi.org/01903/v1.4.1#',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

    # -------------------------------------------------------------------------
    # Overrides for extended XML utilities (support document + security code)
    # -------------------------------------------------------------------------

    def _dian_insert_corporate_registration_scheme_node(self, invoice, xml):
        root = etree.fromstring(xml)
        nsmap = root.nsmap
        corporate_node = etree.Element("{%s}CorporateRegistrationScheme" % nsmap.get('cac'), nsmap=nsmap)
        id_node = etree.SubElement(corporate_node, "{%s}ID" % nsmap.get('cbc'), nsmap=nsmap)
        id_node.text = invoice.journal_id.code
        name_node = etree.SubElement(corporate_node, "{%s}Name" % nsmap.get('cbc'), nsmap=nsmap)
        name_node.text = invoice.company_id.partner_id._get_vat_without_verification_code()
        legal_entity_node = root.find('.//{*}AccountingSupplierParty//{*}PartyLegalEntity')
        if legal_entity_node is not None:
            legal_entity_node.insert(2, corporate_node)
        return etree.tostring(cleanup_xml_node(root))

    def _dian_get_qr_code_url(self, invoice, identifier):
        """ Returns the value used to fill the sts:DianExtensions/sts:QRCode node """
        if invoice.company_id.l10n_co_dian_test_environment:
            url = 'https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey='
        else:
            url = 'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey='
        return url + identifier

    def _dian_get_security_code(self, operation_mode, document_number):
        """ Returns the value for the 'SoftwareSecurityCode' node """
        return sha384((
            operation_mode.dian_software_id
            + operation_mode.dian_software_security_code
            + document_number
        ).encode()).hexdigest()

    def _dian_get_document_type_code(self, invoice):
        """ Returns the document type code for 'InvoiceTypeCode'/'CreditNoteTypeCode' """
        if not invoice.l10n_co_edi_is_support_document and invoice.l10n_co_edi_type:
            return invoice.l10n_co_edi_type.rjust(2, '0')
        elif invoice.move_type == 'in_refund':
            return '95'  # Nota de ajuste al documento soporte
        else:
            return '05'  # Documento soporte

    def _dian_get_customization_id(self, invoice):
        """ Returns the value for the 'CustomizationID' node """
        if not invoice.l10n_co_edi_is_support_document:
            return invoice.l10n_co_edi_operation_type
        return '10' if invoice.partner_id.country_code == 'CO' else '11'

    def _dian_get_operation_mode(self, invoice):
        """Looks for the desired operation mode record based on the mode type."""
        mode = 'bill' if invoice.journal_id.l10n_co_edi_is_support_document else 'invoice'
        return invoice.company_id.l10n_co_dian_operation_mode_ids.filtered(
            lambda operation_mode: operation_mode.dian_software_operation_mode == mode
        )

    def _get_sts_namespace(self, invoice):
        if invoice.l10n_co_edi_debit_note or invoice.move_type == 'out_refund':
            return "http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures"
        else:
            return "dian:gov:co:facturaelectronica:Structures-2-1"

    @api.model
    def _dian_calculate_cude_sha384(self, node, vals):
        """Compute the CUDE for an ApplicationResponse (commercial event).
        See: Section 11.5 of Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9
        """
        cude_vals = {
            'Num_DE': node['cbc:ID']['_text'],
            'Fec_Emi': node['cbc:IssueDate']['_text'],
            'Hor_Emi': node['cbc:IssueTime']['_text'],
            'NitFe': node['cac:SenderParty']['cac:PartyTaxScheme']['cbc:CompanyID']['_text'],
            'DocAdq': node['cac:ReceiverParty']['cac:PartyTaxScheme']['cbc:CompanyID']['_text'],
            'ResponseCode': node['cac:DocumentResponse']['cac:Response']['cbc:ResponseCode']['_text'],
            'ID': node['cac:DocumentResponse']['cac:DocumentReference']['cbc:ID']['_text'],
            'DocumentTypeCode': node['cac:DocumentResponse']['cac:DocumentReference']['cbc:DocumentTypeCode']['_text'],
            'Software-PIN': self._dian_get_operation_mode(vals['invoice']).dian_software_security_code,
        }

        cude = ''.join(str(value) for value in cude_vals.values())
        return sha384(cude.encode()).hexdigest()

    def _dian_sign_xml(self, xml, invoice):
        errors = []
        certificates_sudo = invoice.company_id.sudo().l10n_co_dian_certificate_ids
        operation_mode = self._dian_get_operation_mode(invoice)
        x509_certificates = []
        for cert_sudo in certificates_sudo:
            x509_certificates.append({
                'x509_issuer_description': cert_sudo._get_issuer_string(),
                'x509_serial_number': int(cert_sudo.serial_number),
            })
        root = etree.fromstring(xml)
        namespaces = root.nsmap
        document_number = root.findtext('./cbc:ID', namespaces=namespaces)

        if ((invoice.move_type in ('in_invoice', 'in_refund') and not invoice.l10n_co_edi_is_support_document)
                or (invoice.move_type == 'out_invoice' and self.env.context.get(
                    'l10n_co_next_commercial_state') == 'accepted_by_issuer')):
            identifier = root.findtext('.//cac:DocumentResponse/cac:DocumentReference/cbc:UUID',
                                       namespaces=namespaces)
        else:
            identifier = root.findtext('./cbc:UUID', namespaces=namespaces)

        signature_vals = {
            'record': invoice,
            'sts_namespace': self._get_sts_namespace(invoice),
            'provider_check_digit': invoice.company_id.partner_id._get_vat_verification_code(),
            'provider_id': invoice.company_id.partner_id._get_vat_without_verification_code(),
            'software_id': operation_mode.dian_software_id,
            'software_security_code': self._dian_get_security_code(operation_mode, document_number),
            'qr_code_val': self._dian_get_qr_code_url(invoice, identifier),
            'document_id': "xmldsig-" + str(xml_utils_extend._uuid1()),
            'key_info_id': "xmldsig-" + str(xml_utils_extend._uuid1()) + "-keyinfo",
            'x509_certificate': cert_sudo._get_der_certificate_bytes().decode(),
            'x509_certificates': x509_certificates,
            'signature_value': 'to be filled later',
            'signing_time': datetime.now(tz=timezone('America/Bogota')).isoformat(timespec='milliseconds'),
            'sigcertif_digest': cert_sudo._get_fingerprint_bytes(formatting='base64').decode(),
            'claimed_role': "supplier",
        }
        extensions = self.env['ir.qweb']._render('l10n_co_dian_extended.ubl_extension_dian', signature_vals)
        extensions = cleanup_xml_node(extensions, remove_blank_nodes=False)
        root.insert(0, extensions)
        xml_utils_extend._remove_tail_and_text_in_hierarchy(root)
        # Hash and sign
        xml_utils_extend._reference_digests(
            extensions.find(".//ds:SignedInfo", {'ds': 'http://www.w3.org/2000/09/xmldsig#'}))
        xml_utils_extend._fill_signature(
            extensions.find(".//ds:Signature", {'ds': 'http://www.w3.org/2000/09/xmldsig#'}),
            cert_sudo)
        return etree.tostring(root, encoding='UTF-8'), errors

    # -------------------------------------------------------------------------
    # IMPORT: Track vendor bill XML for RADIAN commercial events
    # -------------------------------------------------------------------------

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        # OVERRIDE: create a document record with the real XML for imported vendor bills
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)
        cufe = self._find_value("./cbc:UUID[@schemeName='CUFE-SHA384']", tree)
        if cufe:
            invoice.l10n_co_edi_cufe_cude_ref = cufe
        if invoice.is_purchase_document() and not invoice.l10n_co_dian_document_ids:
            self.env['l10n_co_dian.document']._create_document(
                etree.tostring(tree, encoding='UTF-8'),
                invoice,
                'invoice_accepted',
                attachment_name=f'dian_{invoice.move_type}_{invoice.ref}.xml',
                commercial_state='pending',
                message_json={'status': ''},
            )
        return logs
