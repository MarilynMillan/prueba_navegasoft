from copy import deepcopy
from hashlib import sha384

from odoo import models
from odoo.exceptions import UserError
from odoo.tools import float_round
from odoo.tools.translate import _
from odoo.addons.l10n_co_edi.models.account_invoice import L10N_CO_EDI_TYPE


class AccountEdiXmlUBLDian(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_dian'

    def _ext_l10n_co_edi_get_product_code(self, move_id, product_id):
        """
        For identifying products, different standards can be used.  If there is a barcode, we take that one, because
        normally in the GTIN standard it will be the most specific one.  Otherwise, we will check the
        :return: (standard, product_code)
        """
        if product_id:
            if move_id.l10n_co_edi_type == L10N_CO_EDI_TYPE['Export Invoice']:
                if not product_id.l10n_co_edi_customs_code:
                    raise UserError(_('Exportation invoices require custom code in all the products, please fill in this information before validating the invoice'))
                return (product_id.l10n_co_edi_customs_code, '020', 'Partida Alanceraria')
            if product_id.barcode:
                return (product_id.barcode, '010', 'GTIN')
            elif product_id.unspsc_code_id:
                return (product_id.unspsc_code_id.code, '001', 'UNSPSC')
            elif product_id.default_code:
                return (product_id.default_code, '999', 'Taxpayer adoption standard')

            raise UserError(_('You must set a barcode, a UNSPSC code or a default code on the product "%s" to be able to generate the UBL DIAN XML.' % product_id.name))

    def _line_group_key(self, grouped_product_id, tax_ids, discount, uom_id):
        rounded_discount = round(discount or 0.0, 6)
        return (grouped_product_id, tuple(sorted(tax_ids)), rounded_discount, uom_id)

    def _base_line_grouping_key(self, base_line):
        line = base_line.get('record')
        return {
            'grouped_product_id': line._nav_grouped_product_id_for_dian() if line else 0,
            'discount': round((line.discount if line else base_line.get('discount', 0.0)) or 0.0, 6),
            'uom_id': (line.product_uom_id.id if line and line._fields.get('product_uom_id') else 0),
        }

    def _reduce_invoice_base_lines_by_variant(self, vals):
        invoice = vals['invoice']
        if invoice.move_type != 'out_invoice' or not invoice._is_dian_grouping_active():
            return
        vals['base_lines'] = self.env['account.tax']._reduce_base_lines_with_grouping_function(
            vals['base_lines'],
            grouping_function=self._base_line_grouping_key,
        )

    def _tax_subtotal_signature(self, subtotal):
        tax_category_vals = subtotal.get('tax_category_vals') or {}
        tax_scheme_vals = tax_category_vals.get('tax_scheme_vals') or {}
        base_unit_measure_attrs = subtotal.get('base_unit_measure_attrs') or {}
        return (
            tax_category_vals.get('percent'),
            tax_scheme_vals.get('id'),
            tax_scheme_vals.get('name'),
            base_unit_measure_attrs.get('unitCode'),
        )

    def _recompute_tax_subtotal_amount(self, subtotal, currency_rounding):
        tax_category_vals = subtotal.get('tax_category_vals') or {}
        percent = tax_category_vals.get('percent')
        taxable_amount = subtotal.get('taxable_amount')
        if percent is None or taxable_amount is None:
            return
        try:
            percent = float(percent)
            taxable_amount = float(taxable_amount)
        except (TypeError, ValueError):
            return
        subtotal['tax_amount'] = float_round(
            taxable_amount * (percent / 100.0),
            precision_rounding=currency_rounding,
            rounding_method='HALF-UP',
        )

    def _recompute_document_tax_totals(self, vals, currency_rounding):
        totals_fields = ('tax_total_vals', 'withholding_tax_total_vals', 'withholding_tax_total_vals_list')
        for field_name in totals_fields:
            for tax_total in vals.get(field_name) or []:
                tax_subtotals = tax_total.get('tax_subtotal_vals') or []
                for subtotal in tax_subtotals:
                    self._recompute_tax_subtotal_amount(subtotal, currency_rounding)
                if tax_subtotals:
                    tax_total['tax_amount'] = sum(subtotal.get('tax_amount', 0.0) for subtotal in tax_subtotals)

    def _refresh_uuid_and_cufe_note(self, move, export_vals):
        cufe_seed = "".join(str(value) for value in self._dian_get_identifier_vals(move, export_vals).values())
        export_vals['vals']['uuid'] = sha384(cufe_seed.encode()).hexdigest()
        note_vals = export_vals['vals'].setdefault('note_vals', [])
        if note_vals:
            note_vals[-1]['note'] = cufe_seed
        else:
            note_vals.append({'note': cufe_seed})

    def _merge_tax_subtotal_vals(self, grouped_tax, incoming_tax, currency_rounding):
        grouped_subtotals = grouped_tax.setdefault('tax_subtotal_vals', [])
        incoming_subtotals = incoming_tax.get('tax_subtotal_vals') or []
        grouped_map = {self._tax_subtotal_signature(subtotal): subtotal for subtotal in grouped_subtotals}
        for incoming_subtotal in incoming_subtotals:
            signature = self._tax_subtotal_signature(incoming_subtotal)
            grouped_subtotal = grouped_map.get(signature)
            if not grouped_subtotal:
                copied_subtotal = deepcopy(incoming_subtotal)
                grouped_subtotals.append(copied_subtotal)
                grouped_map[signature] = copied_subtotal
                continue
            grouped_subtotal['tax_amount'] = grouped_subtotal.get('tax_amount', 0.0) + incoming_subtotal.get('tax_amount', 0.0)
            if 'taxable_amount' in grouped_subtotal or 'taxable_amount' in incoming_subtotal:
                grouped_subtotal['taxable_amount'] = grouped_subtotal.get('taxable_amount', 0.0) + incoming_subtotal.get('taxable_amount', 0.0)
            if 'base_unit_measure' in grouped_subtotal or 'base_unit_measure' in incoming_subtotal:
                grouped_subtotal['base_unit_measure'] = grouped_subtotal.get('base_unit_measure', 0.0) + incoming_subtotal.get('base_unit_measure', 0.0)
            self._recompute_tax_subtotal_amount(grouped_subtotal, currency_rounding)

    def _merge_tax_total_vals(self, grouped_line, incoming_line, field_name, currency_rounding):
        grouped_totals = grouped_line.setdefault(field_name, [])
        incoming_totals = incoming_line.get(field_name) or []
        grouped_map = {tax_total.get('tax_co_type'): tax_total for tax_total in grouped_totals}
        for incoming_tax in incoming_totals:
            tax_co_type = incoming_tax.get('tax_co_type')
            grouped_tax = grouped_map.get(tax_co_type)
            if not grouped_tax:
                copied_tax = deepcopy(incoming_tax)
                grouped_totals.append(copied_tax)
                grouped_map[tax_co_type] = copied_tax
                continue
            grouped_tax['tax_amount'] = grouped_tax.get('tax_amount', 0.0) + incoming_tax.get('tax_amount', 0.0)
            self._merge_tax_subtotal_vals(grouped_tax, incoming_tax, currency_rounding)
            tax_subtotals = grouped_tax.get('tax_subtotal_vals') or []
            if tax_subtotals:
                grouped_tax['tax_amount'] = sum(subtotal.get('tax_amount', 0.0) for subtotal in tax_subtotals)

    def _allowance_signature(self, allowance):
        return (
            allowance.get('charge_indicator'),
            allowance.get('allowance_charge_reason_code'),
            allowance.get('multiplier_factor'),
            bool(allowance.get('from_fixed_tax')),
        )

    def _merge_allowance_charge_vals(self, grouped_line, incoming_line):
        grouped_allowances = grouped_line.setdefault('allowance_charge_vals', [])
        incoming_allowances = incoming_line.get('allowance_charge_vals') or []
        grouped_map = {self._allowance_signature(allowance): allowance for allowance in grouped_allowances}
        for incoming_allowance in incoming_allowances:
            signature = self._allowance_signature(incoming_allowance)
            grouped_allowance = grouped_map.get(signature)
            if not grouped_allowance:
                copied_allowance = deepcopy(incoming_allowance)
                grouped_allowances.append(copied_allowance)
                grouped_map[signature] = copied_allowance
                continue
            grouped_allowance['amount'] = grouped_allowance.get('amount', 0.0) + incoming_allowance.get('amount', 0.0)
            if 'base_amount' in grouped_allowance or 'base_amount' in incoming_allowance:
                grouped_allowance['base_amount'] = grouped_allowance.get('base_amount', 0.0) + incoming_allowance.get('base_amount', 0.0)

    def _merge_price_vals(self, grouped_line, incoming_line):
        grouped_price_vals = grouped_line.setdefault('price_vals', {})
        incoming_price_vals = incoming_line.get('price_vals') or {}
        grouped_quantity = grouped_price_vals.get('base_quantity', 0.0) or 0.0
        incoming_quantity = incoming_price_vals.get('base_quantity', 0.0) or 0.0
        grouped_unit_price = grouped_price_vals.get('price_amount', 0.0) or 0.0
        incoming_unit_price = incoming_price_vals.get('price_amount', 0.0) or 0.0

        total_quantity = grouped_quantity + incoming_quantity
        total_base_amount = (grouped_unit_price * grouped_quantity) + (incoming_unit_price * incoming_quantity)
        grouped_price_vals['base_quantity'] = total_quantity
        grouped_price_vals['price_amount'] = total_base_amount / total_quantity if total_quantity else 0.0

    def _merge_grouped_line_vals(self, grouped_line, incoming_line, currency_rounding):
        grouped_line['line_quantity'] = grouped_line.get('line_quantity', 0.0) + incoming_line.get('line_quantity', 0.0)
        grouped_line['line_extension_amount'] = grouped_line.get('line_extension_amount', 0.0) + incoming_line.get('line_extension_amount', 0.0)
        self._merge_tax_total_vals(grouped_line, incoming_line, 'tax_total_vals', currency_rounding)
        self._merge_tax_total_vals(grouped_line, incoming_line, 'withholding_tax_total_vals_list', currency_rounding)
        self._merge_allowance_charge_vals(grouped_line, incoming_line)
        self._merge_price_vals(grouped_line, incoming_line)

    def _group_line_vals_by_variant(self, move, line_vals):
        grouped_lines = {}
        next_line_id = 1
        account_move_line_model = self.env['account.move.line']
        currency_rounding = move.currency_id.rounding or 0.01
        for line in line_vals:
            line_id = line.get('line_id')
            if not line_id:
                grouped_line = deepcopy(line)
                grouped_line['id'] = next_line_id
                next_line_id += 1
                grouped_lines[('line_without_id', grouped_line['id'])] = grouped_line
                continue

            line_item = account_move_line_model.browse(line_id)
            # In Odoo 18 product invoice lines have display_type='product'.
            # Skip non-commercial lines (tax, cogs, payment_term, note, etc.)
            if not line_item or (line_item.display_type and line_item.display_type != 'product') or line_item.move_id != move:
                grouped_line = deepcopy(line)
                grouped_line['id'] = next_line_id
                next_line_id += 1
                grouped_lines[('line_ungrouped', line_id)] = grouped_line
                continue

            grouping_key = self._line_group_key(
                line_item._nav_grouped_product_id_for_dian(),
                line_item.tax_ids.ids,
                line_item.discount,
                line_item.product_uom_id.id,
            )
            if grouping_key not in grouped_lines:
                grouped_line = deepcopy(line)
                grouped_line['id'] = next_line_id
                next_line_id += 1
                grouped_lines[grouping_key] = grouped_line
                continue
            self._merge_grouped_line_vals(grouped_lines[grouping_key], line, currency_rounding)
        return list(grouped_lines.values())

    def _add_invoice_base_lines_vals(self, vals):
        # Apply grouping in the new DIAN helper flow (dict_to_xml) for out_invoice.
        super()._add_invoice_base_lines_vals(vals)
        self._reduce_invoice_base_lines_by_variant(vals)

    def _export_invoice_vals(self, vals):
        vals = super()._export_invoice_vals(vals)
        move = vals.get('invoice')
        if not move or move.move_type != 'out_invoice' or not move._is_dian_grouping_active():
            return vals

        line_vals = vals['vals'].get('line_vals') or []
        if not line_vals:
            return vals

        grouped_lines = self._group_line_vals_by_variant(move, line_vals)
        vals['vals']['line_vals'] = grouped_lines
        vals['vals']['line_count_numeric'] = len(grouped_lines)
        self._recompute_document_tax_totals(vals['vals'], move.currency_id.rounding or 0.01)
        self._refresh_uuid_and_cufe_note(move, vals)
        return vals

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        line_vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        line_vals['product_id'] = line.product_id.id
        line_vals['line_id'] = line.id
        return line_vals
