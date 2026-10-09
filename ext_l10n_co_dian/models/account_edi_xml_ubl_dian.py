from odoo import models, fields, api, _

class AccountEdiXmlUBLDian(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_dian'

    def _check_on_rewards(self, company_id, product_id, amount=None):
        """Valida si el producto es un descuento/recompensa y retorna el reward."""
        if amount is not None and amount >= 0:
            return False

        # 1. Buscar en rewards directos
        reward = self.env['loyalty.reward'].sudo().search([
            ('active', '=', True),
            ('discount_line_product_id', '=', product_id),
            ('company_id', '=', company_id)
        ], limit=1)

        if reward:
            return reward

        # 2. Buscar en programas de pago (Tarjetas de regalo / E-wallet)
        program = self.env['loyalty.program'].sudo().search([
            ('active', '=', True),
            ('payment_program_discount_product_id', '=', product_id),
            ('company_id', '=', company_id)
        ], limit=1)

        if program and program.payment_program_discount_product_id.id == product_id:
            # Retornamos la recompensa de descuento del programa o True como indicador
            return program.reward_ids.filtered(lambda r: r.reward_type == 'discount')[:1] or True

        return False

    def _get_l10n_co_dian_prorated_discounts(self, invoice):
        """
        Calcula el descuento prorrateado emulando la lógica de POS Loyalty (_applyReward / _getRewardLineValuesDiscount).
        Asegura secuencialidad, agrupación exacta por impuestos y respeto al alcance (scope).
        """
        res = {}
        all_move_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_note', 'line_section'))
        
        # Pre-identificar recompensas (Sincronizado estrictamente con _check_on_rewards)
        product_ids = all_move_lines.mapped('product_id').ids
        company_id = invoice.company_id.id
        
        rewards = self.env['loyalty.reward'].sudo().search([
            ('active', '=', True),
            ('discount_line_product_id', 'in', product_ids),
            ('company_id', '=', company_id)
        ])
        
        payment_programs = self.env['loyalty.program'].sudo().search([
            ('active', '=', True),
            ('payment_program_discount_product_id', 'in', product_ids),
            ('company_id', '=', company_id)
        ])

        reward_product_map = {r.discount_line_product_id.id: r for r in rewards}
        
        for p in payment_programs:
            p_product_id = p.payment_program_discount_product_id.id
            if p_product_id and p_product_id not in reward_product_map:
                # Si el producto coincide con del programa de pago, buscamos su recompensa
                reward = p.reward_ids.filtered(lambda r: r.reward_type == 'discount')[:1]
                reward_product_map[p_product_id] = reward or True

        def get_reward(line):
            # Solo se considera recompensa si el valor es negativo (regla centralizada)
            if line.price_subtotal >= 0:
                return False
            return reward_product_map.get(line.product_id.id)
            
        # Separar líneas
        discount_lines = all_move_lines.filtered(lambda l: l.price_subtotal < 0 or get_reward(l))
        all_positive_lines = all_move_lines.filtered(lambda l: l.price_subtotal > 0 and not get_reward(l))

        if not all_positive_lines:
            return {}

        currency = invoice.currency_id
        remaining_balances = {l.id: l.price_subtotal for l in all_positive_lines}

        def _get_tax_key(line):
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            taxes = taxes.filtered(lambda t: t.amount_type != 'fixed')
            return tuple(sorted(taxes.ids))

        def _is_delivery(line):
            return getattr(line, 'is_delivery', False) or getattr(line.product_id, 'is_delivery', False)

        for d_line in discount_lines:
            amount_to_distribute = abs(d_line.price_subtotal)
            reward = get_reward(d_line)
            d_tax_key = _get_tax_key(d_line)
            
            tax_matched_lines = all_positive_lines.filtered(lambda l: _get_tax_key(l) == d_tax_key)
            if not tax_matched_lines:
                tax_matched_lines = all_positive_lines

            target_lines = self.env['account.move.line']
            if reward:
                applicability = reward.discount_applicability
                if applicability == 'specific':
                    domain = reward._get_discount_product_domain()
                    target_lines = tax_matched_lines.filtered(lambda l: l.product_id.filtered_domain(domain))
                elif applicability == 'cheapest':
                    eligible = tax_matched_lines.filtered(lambda l: not _is_delivery(l))
                    if eligible:
                        min_price = min(eligible.mapped('price_unit'))
                        target_lines = eligible.filtered(lambda l: l.price_unit == min_price)[:1]
                elif reward.reward_type == 'shipping':
                    target_lines = tax_matched_lines.filtered(_is_delivery)
                else: # 'order'
                    if not reward.program_id.is_payment_program:
                        target_lines = tax_matched_lines.filtered(lambda l: not _is_delivery(l))
                    else:
                        target_lines = tax_matched_lines
            else:
                target_lines = tax_matched_lines
            
            if not target_lines:
                target_lines = tax_matched_lines
                
            total_basis = sum(remaining_balances[l.id] for l in target_lines)
            
            if amount_to_distribute > 0 and total_basis > 0:
                remaining_to_share = amount_to_distribute
                target_lines_sorted = target_lines.sorted('id')
                for i, p_line in enumerate(target_lines_sorted):
                    if i == len(target_lines_sorted) - 1:
                        share = remaining_to_share
                    else:
                        share = currency.round(amount_to_distribute * (remaining_balances[p_line.id] / total_basis))
                        remaining_to_share -= share
                    
                    res[p_line.id] = res.get(p_line.id, 0.0) + share
                    remaining_balances[p_line.id] -= share
                    
        return res

    def _thaw(self, d):
        """Helper para convertir frozendict en dict mutable."""
        if isinstance(d, dict):
            return {k: self._thaw(v) for k, v in d.items()}
        if isinstance(d, (list, tuple)):
            return [self._thaw(v) for v in d]
        return d

    def _export_invoice_vals(self, invoice):
        prorated_discounts = self._get_l10n_co_dian_prorated_discounts(invoice)
        self = self.with_context(l10n_co_dian_prorated_discounts=prorated_discounts)
        vals = super()._export_invoice_vals(invoice)
        if not vals.get('taxes_vals'):
            vals['taxes_vals'] = {'tax_details': {}}
        
        if prorated_discounts:
            vals['taxes_vals'] = self._thaw(vals.get('taxes_vals', {}))
            if 'tax_details' not in vals['taxes_vals']:
                vals['taxes_vals']['tax_details'] = {}
            tax_details = vals['taxes_vals']['tax_details']
            
            # 1. Recalcular bases globales restando los descuentos aplicados por línea
            for line in invoice.invoice_line_ids.filtered(lambda l: l.id in prorated_discounts):
                p_amount = prorated_discounts[line.id]
                for grouping_key, details in tax_details.items():
                    if 'base_line_x_taxes_data' in details:
                        for base_line_dict, taxes_data in details['base_line_x_taxes_data']:
                            if base_line_dict['record'].id == line.id:
                                details['base_amount'] = line.currency_id.round(details['base_amount'] - p_amount)
                                details['base_amount_currency'] = details['base_amount']
            
            # 2. Recalcular el total de impuestos de cabecera y la base imponible global
            vals['taxes_vals']['tax_amount_currency'] = sum(
                d['tax_amount_currency'] 
                for k, d in tax_details.items() 
                if not k['tax_co_ret']
            )

            # Sincronizar la base global (utilizada para TaxExclusiveAmount)
            vals['taxes_vals']['base_amount'] = sum(
                d['base_amount']
                for k, d in tax_details.items()
                if not k['tax_co_ret']
            )

            # 3. Actualizar listas derivadas para cac:TaxTotal y cac:WithholdingTaxTotal
            vals['vals']['tax_total_vals'] = self._dian_tax_totals(invoice, vals['taxes_vals'], withholding=False)
            vals['vals']['withholding_tax_total_vals_list'] = self._dian_tax_totals(invoice, vals['taxes_vals'], withholding=True)

            # 4. Sincronizar Legalmonetarytotal (Total de la factura)
            if 'monetary_total_vals' in vals['vals']:
                vals['vals']['monetary_total_vals'] = self._get_invoice_monetary_total_vals(
                    invoice,
                    vals['taxes_vals'],
                    vals['vals']['monetary_total_vals']['line_extension_amount'],
                    0.0, # allowance_total_amount (ya prorrateado en las líneas)
                    0.0, # charge_total_amount
                )

        return vals

    def _fix_multiplier_factor(self, vals_list):
        """Ajusta el multiplier_factor de 1...100 a 0...1 para DIAN."""
        for vals in vals_list:
            if 'multiplier_factor' in vals:
                # Odoo base suele enviar el factor como porcentaje (ej. 10.0 para 10%)
                # DIAN requiere el factor en rango 0...1 (ej. 0.1 para 10%)
                vals['multiplier_factor'] /= 100.0
        return vals_list

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list):
        vals_list = super()._get_invoice_line_allowance_vals_list(line, tax_values_list)
        # Ajustamos los factores que vienen del estándar de Odoo
        self._fix_multiplier_factor(vals_list)
        
        prorated_discounts = self.env.context.get('l10n_co_dian_prorated_discounts', {})
        prorated_amount = prorated_discounts.get(line.id, 0.0)
        
        if prorated_amount > 0:
            currency = line.company_id.currency_id
            base_amount = line.price_subtotal
            
            vals_list.append({
                'currency_name': currency.name,
                'currency_dp': self._get_currency_decimal_places(currency),
                'charge_indicator': 'false',
                'allowance_charge_reason_code': '01',
                'allowance_charge_reason': _("Descuento prorrateado"),
                'amount': prorated_amount,
                'base_amount': base_amount,
                'multiplier_factor': round(prorated_amount / base_amount, 6) if base_amount else 0.0,
            })
            
        return vals_list

    def _get_invoice_allowance_vals_list(self, invoice, taxes_vals):
        vals_list = super()._get_invoice_allowance_vals_list(invoice, taxes_vals)
        return self._fix_multiplier_factor(vals_list)

    def _get_invoice_line_charge_vals_list(self, line, tax_values_list):
        vals_list = super()._get_invoice_line_charge_vals_list(line, tax_values_list)
        return self._fix_multiplier_factor(vals_list)

    def _get_invoice_charge_vals_list(self, invoice, taxes_vals):
        vals_list = super()._get_invoice_charge_vals_list(invoice, taxes_vals)
        return self._fix_multiplier_factor(vals_list)

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        prorated_discounts = self.env.context.get('l10n_co_dian_prorated_discounts', {})
        prorated_amount = prorated_discounts.get(line.id, 0.0)
        
        if prorated_amount > 0:
            # Sincronizamos taxes (iva/retenciones) de la línea
            taxes_vals = self._thaw(taxes_vals or {'tax_details': {}})
            if 'tax_details' not in taxes_vals:
                taxes_vals['tax_details'] = {}
            
            for grouping_key, vals in taxes_vals['tax_details'].items():
                # Ajustar base amount (taxableamount) para que coincida con el lineextensionamount neto.
                vals['base_amount'] = line.currency_id.round(vals['base_amount'] - prorated_amount)
                vals['base_amount_currency'] = vals['base_amount']
            
            # El total de impuestos de la línea
            taxes_vals['tax_amount_currency'] = sum(
                vals['tax_amount_currency'] 
                for k, vals in taxes_vals['tax_details'].items() 
                if not k['tax_co_ret']
            )

        vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        
        if prorated_amount > 0:
            vals['line_extension_amount'] -= prorated_amount
            
        vals['line_product_id'] = line.product_id.id
        return vals

    def _apply_invoice_line_filter(self, line):
        if self._check_on_rewards(line.company_id.id, line.product_id.id, amount=line.price_subtotal):
            return False
        return super()._apply_invoice_line_filter(line)

    def _check_required_fields(self, record, field_names, custom_warning_message=""):
        if record._name == 'product.product':
            rewards = self._check_on_rewards(record.company_id.id, record.id)
            if rewards:
                return
        return super()._check_required_fields(record, field_names, custom_warning_message)