# -*- coding: utf-8 -*-
import logging
import copy
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountMoveSendDebug(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _generate_invoice_documents(self, moves_data, allow_fallback_pdf=False):
        move_ids = [m.id for m in moves_data.keys()]
        _logger.warning("NAVEGA DEBUG: entrando a _generate_invoice_documents para moves %s", move_ids)

        res = super()._generate_invoice_documents(
            moves_data,
            allow_fallback_pdf=allow_fallback_pdf,
        )

        # Log de salida con info útil
        debug_info = {}
        for move, move_data in moves_data.items():
            debug_info[move.id] = {
                "error": move_data.get("error"),
                "edi_format_codes": [
                    edi.edi_format_id.code
                    for edi in move_data.get("edi_document_ids", self.env["account.edi.document"])
                ] if move_data.get("edi_document_ids") else [],
            }

        _logger.warning("NAVEGA DEBUG: salida de _generate_invoice_documents: %s", debug_info)

        return res
    
    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        _logger.warning(
            "NAVEGA DEBUG: entrando a _generate_and_send_invoices para moves %s | from_cron=%s allow_raising=%s allow_fallback_pdf=%s custom_settings=%s",
            moves.ids, from_cron, allow_raising, allow_fallback_pdf, custom_settings,
        )
        res = super()._generate_and_send_invoices(
            moves,
            from_cron=from_cron,
            allow_raising=allow_raising,
            allow_fallback_pdf=allow_fallback_pdf,
            **custom_settings,
        )
        _logger.warning("NAVEGA DEBUG: _generate_and_send_invoices terminó para moves %s", moves.ids)
        return res
        
class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_co_edi_generate_xml(self, invoice):
        _logger.warning("NAVEGA DEBUG: _l10n_co_edi_generate_xml para factura %s (%s)", invoice.name, invoice.id)
        xml = super()._l10n_co_edi_generate_xml(invoice)
        _logger.warning("NAVEGA DEBUG: longitud XML generado para %s: %s bytes", invoice.name, len(xml) if xml else 'None')
        return xml

class L10nCoDianDebugUbl20(models.AbstractModel):
    """
    Esta clase hereda el motor de UBL que DIAN está extendiendo.
    Odoo 18 para DIAN usa account.edi.xml.ubl_20 como base en l10n_co_dian.
    """
    _inherit = 'account.edi.xml.ubl_20'

    def _export_invoice_vals(self, invoice):
        """
        Punto clave: aquí DIAN arma todos los vals que luego se convierten en XML.
        """
        _logger.warning(
            "NAVEGA DEBUG DIAN: entrando _export_invoice_vals | move=%s | provider=%s | move_type=%s",
            invoice.name,
            getattr(invoice.company_id, 'l10n_co_dian_provider', None),
            invoice.move_type,
        )
        vals = super()._export_invoice_vals(invoice)
        # OJO: vals es un dict con muchas cosas, no logueamos todo para no explotar el log
        taxes_details = vals.get('taxes_vals', {}).get('tax_details', {}) if vals else {}
        _logger.warning(
            "NAVEGA DEBUG DIAN: salida _export_invoice_vals | move=%s | tax_details_keys=%s",
            invoice.name,
            list(taxes_details.keys()),
        )
        return vals

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        """
        Aquí se calculan los totales monetarios que luego DIAN usa para CUFE y FAT07.
        """
        _logger.warning(
            "NAVEGA DEBUG DIAN: entrando _get_invoice_monetary_total_vals | move=%s | base_amount=%.2f",
            invoice.name,
            taxes_vals.get('base_amount', 0.0),
        )
        res = super()._get_invoice_monetary_total_vals(
            invoice,
            taxes_vals,
            line_extension_amount,
            allowance_total_amount,
            charge_total_amount,
        )
        _logger.warning(
            "NAVEGA DEBUG DIAN: salida _get_invoice_monetary_total_vals | move=%s | monetary_total=%s",
            invoice.name,
            res,
        )
        return res


class L10nCoDianDebugTaxTotals(models.AbstractModel):
    """
    Heredamos también para enganchar el método específico de DIAN
    que agrupa los impuestos: _dian_tax_totals.
    """
    _inherit = 'account.edi.xml.ubl_20'

    def _dian_tax_totals(self, move, taxes_vals, withholding):
        _logger.warning(
            "NAVEGA DEBUG DIAN: entrando _dian_tax_totals | move=%s | withholding=%s | tax_details_len=%s",
            move.name,
            withholding,
            len(taxes_vals.get('tax_details', {})),
        )
        res = super()._dian_tax_totals(move, taxes_vals, withholding)
        _logger.warning(
            "NAVEGA DEBUG DIAN: salida _dian_tax_totals | move=%s | withholding=%s | result=%s",
            move.name,
            withholding,
            res,
        )
        return res

class L10nCoDianDebugExport(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        """
        Hook de debug: aquí se llama cuando DIAN genera el XML antes de firmar.
        Ojo: hay que respetar la firma original con `convert_fixed_taxes`.
        """
        _logger.warning(
            "NAVEGA DEBUG DIAN: entrando _export_invoice | move=%s | provider=%s | tipo=%s | convert_fixed_taxes=%s",
            invoice.name,
            getattr(invoice.company_id, 'l10n_co_dian_provider', None),
            invoice.move_type,
            convert_fixed_taxes,
        )
        xml, errors = super()._export_invoice(invoice, convert_fixed_taxes=convert_fixed_taxes)
        _logger.warning(
            "NAVEGA DEBUG DIAN: salida _export_invoice | move=%s | xml_len=%s | errors=%s",
            invoice.name,
            len(xml or b'') if xml else 0,
            errors,
        )
        return xml, errors

class L10nCoDianDebugExport(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_dian"

    def _dian_tax_totals(self, move, taxes_vals, withholding):
        """Extiende el cálculo de TaxTotal / WithholdingTaxTotal para:
        - Registrar en log lo que se está enviando
        - Omitir retenciones (withholding) cuyo valor sea 0, para evitar FAT07
        """
        # Llamamos primero al comportamiento estándar (l10n_co_dian)
        res = super()._dian_tax_totals(move, taxes_vals, withholding)

        _logger.warning(
            "NAVEGA DEBUG DIAN: _dian_tax_totals (ANTES FILTRO) | move=%s | withholding=%s | res=%s",
            move.name,
            withholding,
            res,
        )

        currency = move.company_id.currency_id

        # Si NO es retención, devolvemos tal cual
        if not withholding:
            return res

        # Para retenciones: no enviar impuestos con monto 0
        filtered = []
        for tt in res:
            tax_type = tt.get("tax_co_type")
            tax_amount = tt.get("tax_amount", 0.0)

            if currency.is_zero(tax_amount):
                _logger.warning(
                    "NAVEGA DEBUG DIAN: omitiendo retención en XML por monto 0 | move=%s | tax_type=%s | tax_amount=%s",
                    move.name,
                    tax_type,
                    tax_amount,
                )
                continue

            filtered.append(tt)

        _logger.warning(
            "NAVEGA DEBUG DIAN: _dian_tax_totals (DESPUÉS FILTRO) | move=%s | withholding=%s | res=%s",
            move.name,
            withholding,
            filtered,
        )

        return filtered

class AccountMove(models.Model):
    _inherit = "account.move"

    def _nav_tax_totals_filtered(self, tax_totals=None):
        """
        Helper para el QWeb l10n_co_dian.report_invoice_document.

        - Si el template nos pasa tax_totals, usamos ese.
        - Si no, usamos el campo JSON estándar `tax_totals` de account.move.
        De momento no aplicamos lógica extra, solo devolvemos lo que ya calculó Odoo.
        """
        self.ensure_one()

        if tax_totals is None:
            tax_totals = self.tax_totals or {}

        _logger.warning(
            "NAVEGA DEBUG DIAN: _nav_tax_totals_filtered | move=%s | tax_totals=%s",
            self.name,
            tax_totals,
        )
        return tax_totals

    def _nav_get_tax_amount_by_group_filtered(self):
        """
        Versión filtrada de _get_tax_amount_by_group() para IMPRESIÓN en account.move:
        - Oculta líneas de impuestos con monto 0
        - (Opcional) puedes filtrar aquí autoretenciones por nombre
        """
        self.ensure_one()
        # Estructura típica: [(name, tax_amount, base_amount, tax_group_id), ...]
        res = self._get_tax_amount_by_group()
        currency = self.currency_id or self.company_currency_id

        filtered = []
        for amount_by_group in res:
            name = amount_by_group[0]
            amount = amount_by_group[1]

            # 1) Ocultar impuestos con monto 0
            if currency and currency.is_zero(amount):
                _logger.warning(
                    "NAVEGA DEBUG: omitiendo impuesto 0 en totales factura | move=%s | grupo=%s | amount=%s",
                    self.name,
                    name,
                    amount,
                )
                continue

            # 2) (OPCIONAL) ocultar autoretención por nombre del grupo
            # if 'Autoret' in (name or '') or 'ReteRenta' in (name or ''):
            #     _logger.warning(
            #         "NAVEGA DEBUG: omitiendo autoretención en totales factura | move=%s | grupo=%s | amount=%s",
            #         self.name,
            #         name,
            #         amount,
            #     )
            #     continue

            filtered.append(amount_by_group)

        _logger.warning(
            "NAVEGA DEBUG: _nav_get_tax_amount_by_group_filtered (account.move) | move=%s | result=%s",
            self.name,
            filtered,
        )
        return filtered
    
    def _nav_tax_totals_filtered_print(self, tax_totals=None):
        """
        Devuelve una versión filtrada de tax_totals para impresión:
        - Elimina líneas de impuestos cuyo amount == 0.0 (ej: autorretención 0)
        Se usa desde QWeb en lugar de usar o.tax_totals directamente.
        """
        self.ensure_one()

        if not tax_totals:
            tax_totals = self.tax_totals or {}

        # Clonar para no modificar el JSON original
        filtered = copy.deepcopy(tax_totals)

        currency = self.currency_id or self.company_currency_id
        if not filtered:
            return filtered

        groups_by_subtotal = filtered.get("groups_by_subtotal") or {}

        for subtotal_name, lines in list(groups_by_subtotal.items()):
            new_lines = []
            for line in lines:
                amount = line.get("amount", 0.0)
                # Si el monto es 0, no lo mostramos
                if currency and currency.is_zero(amount):
                    _logger.warning(
                        "NAVEGA DEBUG DIAN: omitiendo IMPUESTO 0 en totales impresión | "
                        "move=%s | subtotal=%s | tax_group=%s | amount=%s",
                        self.name,
                        subtotal_name,
                        line.get("tax_group_name") or line.get("group_key"),
                        amount,
                    )
                    continue
                new_lines.append(line)

            if new_lines:
                groups_by_subtotal[subtotal_name] = new_lines
            else:
                groups_by_subtotal.pop(subtotal_name)

        filtered["groups_by_subtotal"] = groups_by_subtotal

        _logger.warning(
            "NAVEGA DEBUG DIAN: _nav_tax_totals_filtered_print | move=%s | result=%s",
            self.name,
            filtered,
        )
        return filtered

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _nav_tax_labels_filtered(self):
        """
        Devuelve el texto de la columna 'Taxes' para la línea,
        ocultando la AUTORRETENCIÓN cuando su monto en el total
        de la factura es 0.

        Lógica:
        - Revisamos o.tax_totals para ver si el grupo 'ReteRenta'
          (o el nombre que use la agrupación) tiene amount == 0.
        - Si es 0, ocultamos de la etiqueta de la línea cualquier tax
          cuyo nombre/label contenga 'ReteRenta'.
        """
        self.ensure_one()
        move = self.move_id
        tax_totals = move.tax_totals or {}
        hide_autoret = False

        groups_by_subtotal = (tax_totals.get("groups_by_subtotal") or {})
        currency = move.currency_id or move.company_currency_id

        # Detectar si la ReteRenta total es 0 en la factura
        for _subtotal_name, lines in groups_by_subtotal.items():
            for line_dict in lines:
                group_name = (line_dict.get("tax_group_name") or "").strip()
                amount = line_dict.get("amount", 0.0)
                # Ajusta 'ReteRenta' si tu grupo de impuesto se llama distinto
                if "ReteRenta" in group_name and currency.is_zero(amount):
                    hide_autoret = True
                    _logger.warning(
                        "NAVEGA DEBUG DIAN: detección de autoretención 0 para ocultar en líneas | move=%s | group=%s | amount=%s",
                        move.name,
                        group_name,
                        amount,
                    )
                    break
            if hide_autoret:
                break

        labels = []
        for tax in self.tax_ids:
            label = tax.invoice_label or tax.name or ""
            if hide_autoret and "ReteRenta" in label:
                _logger.warning(
                    "NAVEGA DEBUG DIAN: ocultando autoretención en línea | move=%s | line_id=%s | tax=%s",
                    move.name,
                    self.id,
                    label,
                )
                continue
            labels.append(label)

        return ", ".join(labels)

    def _nav_line_taxes_print(self):
        """
        Devuelve la lista de impuestos de la línea para IMPRESIÓN.

        Lógica:
        - Calcula impuestos con compute_all (teniendo en cuenta descuento).
        - Agrupa por tax_group (o por tax_group_id).
        - Si la suma de amount del grupo es 0 (autoretención + contratax), NO se imprime.
        - Evita duplicar etiquetas: 1 etiqueta por grupo que quede con monto != 0.
        """
        self.ensure_one()

        if not self.tax_ids:
            return ""

        move = self.move_id
        currency = move.currency_id or move.company_currency_id

        # Tener en cuenta el descuento en el cálculo
        price_unit_wo_discount = self.price_unit * (1 - (self.discount or 0.0) / 100.0)

        res = self.tax_ids.compute_all(
            price_unit_wo_discount,
            currency=currency,
            quantity=self.quantity,
            product=self.product_id,
            partner=move.partner_id,
        )

        # Agrupar por tax_group para detectar autoretenciones (monto neto 0)
        groups = {}
        for tax_res in res.get("taxes", []):
            amount = tax_res.get("amount", 0.0)
            tax_id = tax_res.get("id")
            tax_rec = self.tax_ids.browse(tax_id) if tax_id else False

            # Clave de grupo: usa tax_group_id si viene en el dict, si no usa tax_id.
            group_key = tax_res.get("tax_group_id") or tax_id

            label = (
                (tax_rec.invoice_label or tax_rec.name)
                if tax_rec
                else tax_res.get("name")
            )

            if group_key not in groups:
                groups[group_key] = {
                    "amount": 0.0,
                    "label": label,
                    "tax": tax_rec,
                }

            groups[group_key]["amount"] += amount
            # Si encontramos una etiqueta más "bonita" después, la podemos actualizar
            if label and not groups[group_key]["label"]:
                groups[group_key]["label"] = label

        labels = []
        for group_key, data in groups.items():
            amount = data["amount"]
            label = data["label"]
            tax_rec = data["tax"]

            # Si el monto neto del grupo es 0 → no mostramos (caso autoretención + contratax)
            if currency and currency.is_zero(amount):
                _logger.warning(
                    "NAVEGA DEBUG DIAN: omitiendo GRUPO TAX 0 en línea impresión | "
                    "move=%s | line_id=%s | group=%s | label=%s | amount=%s",
                    move.name,
                    self.id,
                    group_key,
                    label,
                    amount,
                )
                continue

            if label and label not in labels:
                labels.append(label)

        return ", ".join(labels)

