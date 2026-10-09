# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from datetime import datetime
from .utils import (
    nav_line_stable_key,
    nav_get_threshold_tax_ids,
    nav_merge_preserving_non_threshold,
    nav_unique_tax_recordset,
)


# =========================================================
# account.move (Factura) - Cálculos de retenciones y DIAN
# =========================================================
class AccountInvoice(models.Model):
    """ This Model calculates and saves withholding tax that apply in Colombia """
    _description = 'Model to create and save withholding taxes'
    _name = 'account.move'
    _inherit = 'account.move'
    # -------------------------
    # Optimización calcularimpuestos
    # -------------------------
    def calcularimpuestos(self):
        """Recalcula impuestos usando el mismo motor de onchange/compute para evitar toggles."""
        invoices = self.filtered(lambda move: move.is_invoice(include_receipts=True))
        invoices._nav_recompute_invoice_line_taxes(use_write=True)

    # -------------------------
    # DIAN: helper (se deja como está pero no se usa como compute)
    # -------------------------
    def _get_has_valid_dian_info_JSON(self):
        if self.journal_id.sequence_id.use_dian_control:

            remaining_numbers = self.journal_id.sequence_id.remaining_numbers
            remaining_days = self.journal_id.sequence_id.remaining_days
            dian_resolution = self.env['ir.sequence.dian_resolution'].search([
                ('sequence_id', '=', self.journal_id.sequence_id.id),
                ('active_resolution', '=', True)
            ])
            today = fields.Datetime.now()

            not_valid = False
            spent = False
            if len(dian_resolution) == 1 and self.state == 'draft':
                dian_resolution.ensure_one()

                date_to = datetime.strptime(dian_resolution['date_to'].strftime('%Y-%m-%d'), '%Y-%m-%d')
                days = (date_to - today).days

                if dian_resolution['number_to'] - dian_resolution['number_next'] < remaining_numbers or days < remaining_days:
                    not_valid = True

                if dian_resolution['number_next'] > dian_resolution['number_to']:
                    spent = True

            if spent:
                pass  # resolution spent, keeping numbers
            self.not_has_valid_dian = not_valid

    # -------------------------
    # Totales auxiliares (no pisamos amount_total estándar)
    # -------------------------
    wh_taxes = fields.Monetary(
        'Withholding Tax',
        compute="_compute_withholding_amounts",
        store=True,
        readonly=True,
        compute_sudo=True,
    )
    amount_without_wh_tax = fields.Monetary(
        'Total With Tax',
        compute="_compute_withholding_amounts",
        store=True,
        readonly=True,
        compute_sudo=True,
    )
    invoice_date = fields.Date(required=False)

    # Mantienes tu campo así como lo definiste
    not_has_valid_dian = fields.Boolean("a")  # (compute='_get_has_valid_dian_info_JSON')

    # ⚠️ Mantenemos tu redefinición de tax_line_ids, tal cual la pediste
    tax_line_ids = fields.One2many(
        'account.tax', 'id',
        string='taxes',
        help='This field show related taxes applied to this tax'
    )

    resolution_number = fields.Char('Resolution number in invoice')
    resolution_date = fields.Date()
    resolution_date_to = fields.Date()
    resolution_number_from = fields.Integer("desde")
    resolution_number_to = fields.Integer("hasta")

    @api.onchange('fiscal_position_id')
    def _compute_fiscal_position_add(self):
        self._nav_recompute_invoice_line_taxes(use_write=False)

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_lines_recompute_taxes(self):
        self._nav_recompute_invoice_line_taxes(use_write=False)

    def _nav_recompute_invoice_line_taxes(self, use_write=True):
        for record in self:
            existing_by_line = {nav_line_stable_key(line): line.tax_ids for line in record.invoice_line_ids}
            global_applicable_base = record._nav_get_global_applicable_rete_base()
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, record.company_id)
            line_updates = []
            for line in record.invoice_line_ids:
                if line.display_type in ('line_section', 'line_note'):
                    continue
                if line.nav_disable_rete_base_calc_line:
                    continue
                line_base = line._nav_get_rete_base_for_move(global_applicable_base=global_applicable_base)
                computed_taxes = line.with_context(
                    nav_base_retenciones_override=line_base
                )._get_computed_taxes()
                computed_taxes = nav_unique_tax_recordset(computed_taxes)
                include_product_taxes = (
                    not line.nav_manual_tax_override
                    and not (line._origin and line._origin.id)
                )
                taxes = nav_merge_preserving_non_threshold(
                    nav_unique_tax_recordset(line.tax_ids),
                    computed_taxes,
                    threshold_tax_ids,
                    include_computed_non_threshold=include_product_taxes,
                )
                current_tax_ids = set(nav_unique_tax_recordset(line.tax_ids).ids)
                new_tax_ids = set(taxes.ids)
                if line.base_retenciones == line_base and current_tax_ids == new_tax_ids:
                    continue
                vals = {
                    'base_retenciones': line_base,
                    'tax_ids': [Command.set(taxes.ids)],
                }
                if use_write and record.id and isinstance(line.id, int):
                    line_updates.append(Command.update(line.id, vals))
                else:
                    # In onchange, update all rows in-memory so other lines refresh immediately.
                    line.with_context(nav_skip_manual_mark=True).update(vals)
            if use_write and line_updates:
                record.with_context(nav_skip_invoice_recompute=True).write({'invoice_line_ids': line_updates})

    def _nav_get_global_applicable_rete_base(self):
        self.ensure_one()
        if not self.company_id.nav_rete_use_global_applicable_base:
            return 0.0
        total = 0.0
        for line in self.invoice_line_ids:
            if line.display_type in ('line_section', 'line_note'):
                continue
            line_base = line._nav_get_rete_base_immediate()
            if line_base <= 0.0:
                continue
            if line.product_id and not line.product_id.product_tmpl_id.nav_rete_is_applicable:
                continue
            total += line_base
        return total

    # Conservamos tu método original pero te recomiendo NO usarlo para pisar totales;
    # te dejo un compute separado abajo que no interfiere con amount_total.
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def _compute_amount2(self):
        super(AccountInvoice, self)._compute_amount()
        fp_company = self.env['account.fiscal.position'].search(
            [('id', '=', self.company_id.partner_id.property_account_position_id.id)]
        )
        company_tax_ids = [base_tax.tax_id.id for base_tax in fp_company.tax_ids_invoice]

        hw_taxes = 0
        amount_without_hw_tax = 0
        if self.fiscal_position_id:
            fp_partner = self.env['account.fiscal.position'].search(
                [('id', '=', self.fiscal_position_id.id)]
            )
            partner_tax_ids = [base_tax.tax_id.id for base_tax in fp_partner.tax_ids_invoice]

            for line in self.line_ids.filtered(lambda l: l.tax_repartition_line_id and not l.tax_line_id.dont_impact_balance):
                # if line.tax_line_id.id not in (partner_tax_ids + company_tax_ids):
                #     amount_without_hw_tax += line.balance
                pass

            # Evita usar tu tax_line_ids redefinido para totales
            # self.amount_tax = sum(line.amount_total for line in self.tax_line_ids if not line.tax_id.dont_impact_balance)
            self.amount_tax = sum(line.balance for line in self.line_ids)
            self.wh_taxes = abs(sum(line.balance for line in self.line_ids))
        else:
            # self.amount_tax = sum(line.amount for line in self.tax_line_ids if line.tax_id.id not in company_tax_ids)
            self.amount_tax = sum(line.balance for line in self.line_ids)

        self.wh_taxes = hw_taxes
        # Evita pisar amount_total estándar:
        # self.amount_total -= hw_taxes
        self.amount_without_wh_tax = self.amount_untaxed + self.amount_tax
        # self.amount_total = self.amount_without_wh_tax - self.wh_taxes

    # Compute recomendado para mostrar retención y total sin retención
    @api.depends('line_ids.balance', 'line_ids.tax_line_id', 'company_id', 'currency_id')
    def _compute_withholding_amounts(self):
        for move in self:
            tax_std = sum(
                move.line_ids.filtered(
                    lambda l: l.tax_repartition_line_id and l.tax_line_id and not l.tax_line_id.dont_impact_balance
                ).mapped('balance')
            )
            wh_val = sum(
                move.line_ids.filtered(
                    lambda l: l.tax_repartition_line_id and l.tax_line_id and l.tax_line_id.dont_impact_balance
                ).mapped('balance')
            )
            move.wh_taxes = abs(wh_val)
            move.amount_without_wh_tax = move.amount_untaxed + tax_std

    @api.onchange('invoice_date')
    def _onchange_invoice_date(self):
        if self.invoice_date:
            if not self.invoice_payment_term_id:
                self.invoice_date_due = self.invoice_date
            self.date = self.invoice_date


# =========================================================
# account.tax (Impuesto)
# =========================================================
class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    tax_in_invoice = fields.Boolean(
        string="Evaluate in invoice", default=False,
        help="Check this if you want to hide the tax from the taxes list in products"
    )
    based_tax_group = fields.Boolean(
        string="Based on Tax Group", default=False,
        help="Check this if you want to show the field taxes group list"
    )

    # Grupo de impuestos de encabezado
    tax_group_id_header = fields.Many2one('account.tax.group', string="Tax Group")

    dont_impact_balance = fields.Boolean(
        string="Don't impact balance", default=False,
        help="Check this if you want to assign counterpart taxes accounts"
    )
    account_id_counterpart = fields.Many2one(
        'account.account', string='Tax Account Counterpart', ondelete='restrict',
        help="Account that will be set on invoice tax lines for invoices. Leave empty to use the expense account."
    )
    refund_account_id_counterpart = fields.Many2one(
        'account.account', string='Tax Account Counterpart on Refunds', ondelete='restrict',
        help="Account that will be set on invoice tax lines for refunds. Leave empty to use the expense account."
    )
    position_id = fields.Many2one('account.fiscal.position', string='Fiscal position related id')
    base_taxes = fields.One2many(
        'account.base.tax', 'tax_id', string='Base taxes',
        help='This field show related taxes applied to this tax'
    )

    # Campos auxiliares
    base = fields.Float(digits=(16, 2), default=0.0, string="Base")
    amount_total = fields.Float(digits=(16, 2), default=0.0, string="Total")

    def unlink(self, default=None):
        # Más eficiente con search_count
        if self.env['account.fiscal.position.base.tax'].search_count([('tax_id', 'in', self.ids)]):
            raise UserError(_('No se puede eliminar un impuesto esta asignado a una posicion fiscal'))
        return super(AccountTax, self).unlink()


# =========================================================
# account.base.tax (Vigencias/umbrales de base)
# =========================================================
class AccountBaseTax(models.Model):
    _name = 'account.base.tax'
    _description = 'Account Base Tax'

    tax_id = fields.Many2one('account.tax', string='Tax related', required=True)
    start_date = fields.Date(string='Since date', required=True)
    end_date = fields.Date(string='Until date', required=True)
    amount = fields.Float(digits=(16, 2), default=0.0, string="Tax amount", required=True)

    @api.constrains('start_date', 'end_date')
    def _check_closing_date(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("Error! End date cannot be set before start date."))

    @api.constrains('start_date', 'end_date', 'tax_id')
    def _dont_overlap_date(self):
        for rec in self:
            if not rec.start_date or not rec.end_date or not rec.tax_id:
                continue
            overlap = self.search_count([
                ('start_date', '<=', rec.end_date),
                ('end_date', '>=', rec.start_date),
                ('tax_id', '=', rec.tax_id.id),
                ('id', '!=', rec.id),
            ])
            if overlap:
                raise ValidationError(_("Error! cannot have overlap date range."))


# =========================================================
# account.tax.group (Bandera de impresión)
# =========================================================
class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _inherit = 'account.tax.group'

    not_in_invoice = fields.Boolean(
        string="Don't show in invoice", default=False,
        help="Check this if you want to hide the taxes in this group when print an invoice"
    )


# =========================================================
# Relación posición fiscal ↔ impuestos base
# =========================================================
class AccountFiscalPositionTaxes(models.Model):
    _name = 'account.fiscal.position.base.tax'
    _description = 'Account Fiscal Position Base Tax'

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal position related', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax', required=True)
    amount = fields.Float(related='tax_id.amount', store=True, readonly=True)
    account_journal_ids = fields.Many2many(
        'account.journal', 'account_journal_taxes_ids_rel', 'tax_id', 'journal_id', 'Journal'
    )
    # _sql_constraints = [
    #     ('tax_fiscal_position_uniq', 'unique(position_id, tax_id)', _('Error! cannot have repeated taxes'))
    # ]


# =========================================================
# account.fiscal.position (map_tax_rete integrado acá)
# =========================================================
class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = 'account.fiscal.position'

    tax_ids_invoice = fields.One2many(
        'account.fiscal.position.base.tax', 'position_id',
        string='Taxes that refer to the fiscal position'
    )

    @api.model
    def map_tax_rete(self, journal, fecha, product=None, partner=None, base_retenciones=0.0):
        """Devuelve impuestos de retención vigentes según diario y base."""
        Tax = self.env['account.tax']
        # Si self es un set, no operamos; trabaja por registro
        if not self or (hasattr(self, 'ids') and len(self.ids) != 1):
            return Tax.browse()

        items = self.tax_ids_invoice
        if journal:
            items = items.filtered(lambda i: not i.account_journal_ids or journal in i.account_journal_ids)

        result_tax_ids = set()
        for it in items:
            for bt in it.tax_id.base_taxes:
                if bt.start_date and bt.end_date and (bt.start_date <= fecha <= bt.end_date):
                    if base_retenciones >= (bt.amount or 0.0):
                        result_tax_ids.add(it.tax_id.id)
                    # break

        return Tax.browse(list(result_tax_ids))


# =========================================================
# account.move.line (líneas) - cálculo de impuestos por línea
# =========================================================
class AccountInvoiceLine(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'

    dont_impact_balance_inside = fields.Boolean("dont_impact_balance_inside", default=False)
    dont_impact_balance = fields.Boolean("dont_impact_balance")
    account_id_counterpart = fields.Many2one("account.account")
    refund_account_id_counterpart = fields.Many2one("account.account")
    base_retenciones = fields.Float("Si cumple la base", default=0.0)
    nav_disable_rete_base_calc_line = fields.Boolean(
        string="Deshabilitar cálculo de bases de retención",
        default=False,
    )
    nav_manual_tax_override = fields.Boolean(
        string="Edición manual de impuestos",
        default=False,
        copy=False,
    )
    @api.onchange('tax_ids')
    def _onchange_mark_manual_tax_override(self):
        if self.env.context.get('nav_skip_manual_mark'):
            return
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                continue
            if not line.move_id or not line.move_id.is_invoice(include_receipts=True):
                continue
            if not line.product_id and not line.tax_ids:
                continue
            threshold_tax_ids = nav_get_threshold_tax_ids(
                self.env,
                line.move_id.company_id or line.company_id,
            )
            current_taxes = nav_unique_tax_recordset(line.tax_ids)
            computed_taxes = nav_unique_tax_recordset(line._get_computed_taxes())
            current_non_threshold = set(current_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            computed_non_threshold = set(computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            if current_non_threshold == computed_non_threshold:
                continue
            line.nav_manual_tax_override = True

    @api.depends(
    'product_id', 'product_uom_id',
    'account_id', 'account_id.tax_ids',
    'company_id',
    'move_id.fiscal_position_id',   # << clave para que cambie al seleccionar Posición Fiscal
    'price_unit', 'quantity', 'discount', 'base_retenciones',
    )
    def _compute_tax_ids(self):
        existing_by_line = {nav_line_stable_key(line): line.tax_ids for line in self}
        threshold_tax_ids = nav_get_threshold_tax_ids(self.env, self[:1].company_id) if self else set()
        for line in self:
            if line.nav_manual_tax_override or line.nav_disable_rete_base_calc_line:
                continue
            if line.display_type in ('line_section', 'line_note'):
                continue
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            if not (line._origin and line._origin.id):
                continue
            current_taxes = nav_unique_tax_recordset(line.tax_ids)
            computed_taxes = nav_unique_tax_recordset(line._get_computed_taxes())
            current_non_threshold = set(current_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            computed_non_threshold = set(computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            if current_non_threshold != computed_non_threshold:
                line.nav_manual_tax_override = True
        unlocked_lines = self.filtered(
            lambda l: not l.nav_disable_rete_base_calc_line and not l.nav_manual_tax_override
        )
        if unlocked_lines:
            super(AccountInvoiceLine, unlocked_lines)._compute_tax_ids()
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                continue
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            if line.nav_disable_rete_base_calc_line:
                previous_taxes = existing_by_line.get(nav_line_stable_key(line))
                if previous_taxes is not None:
                    line.tax_ids = nav_unique_tax_recordset(previous_taxes)
                continue
            # Siempre recalcula al tener producto o impuestos en cuenta
            if line.product_id or line.account_id.tax_ids or not line.tax_ids:
                computed_taxes = nav_unique_tax_recordset(line._get_computed_taxes())
                if line._origin and line._origin.id:
                    previous_taxes = existing_by_line.get(nav_line_stable_key(line))
                else:
                    previous_taxes = line.tax_ids
                previous_taxes = nav_unique_tax_recordset(previous_taxes)
                include_product_taxes = (
                    not line.nav_manual_tax_override
                    and not (line._origin and line._origin.id)
                )
                line.tax_ids = nav_merge_preserving_non_threshold(
                    previous_taxes,
                    computed_taxes,
                    threshold_tax_ids,
                    include_computed_non_threshold=include_product_taxes,
                )

    @api.onchange('price_unit', 'quantity', 'discount', 'product_id', 'account_id')
    def _onchange_recompute_move_retention_taxes(self):
        moves = self.mapped('move_id').filtered(lambda move: move.is_invoice(include_receipts=True))
        if moves:
            moves._nav_recompute_invoice_line_taxes(use_write=False)

    def _nav_get_rete_base_immediate(self):
        self.ensure_one()
        qty = self.quantity or 0.0
        price = self.price_unit or 0.0
        disc = (self.discount or 0.0) / 100.0
        return price * qty * (1.0 - disc)

    def _nav_is_rete_applicable_product(self):
        self.ensure_one()
        if self._nav_get_rete_base_immediate() <= 0.0:
            return False
        return not self.product_id or self.product_id.product_tmpl_id.nav_rete_is_applicable

    def _nav_get_rete_base_for_move(self, global_applicable_base=None):
        self.ensure_one()
        company = self.move_id.company_id or self.company_id
        if not company.nav_rete_use_global_applicable_base:
            return self._nav_get_rete_base_immediate()
        if not self._nav_is_rete_applicable_product():
            return 0.0
        if global_applicable_base is not None:
            return global_applicable_base
        return self.move_id._nav_get_global_applicable_rete_base() if self.move_id else 0.0

    def _nav_filter_taxes_by_rules(self, taxes, fecha, base_ret):
        self.ensure_one()
        valid_taxes = self.env['account.tax']
        for tax in taxes:
            if not tax.base_taxes:
                valid_taxes |= tax
                continue
            if any(
                bt.start_date and bt.end_date
                and (bt.start_date <= fecha <= bt.end_date)
                and base_ret >= (bt.amount or 0.0)
                for bt in tax.base_taxes
            ):
                valid_taxes |= tax
        return valid_taxes

    def _nav_map_taxes_with_fp(self, fp, taxes):
        self.ensure_one()
        if not fp or not taxes:
            return taxes
        try:
            return fp.map_tax(taxes)
        except TypeError:
            pass
        try:
            return fp.map_tax(taxes, partner=self.move_id.partner_id)
        except TypeError:
            return taxes

    def _nav_get_invoice_base_taxes_fresh(self):
        self.ensure_one()
        Tax = self.env['account.tax']
        company = self.move_id.company_id or self.company_id

        if self.move_id.is_sale_document(include_receipts=True):
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda t: t.company_id == company)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids.filtered(lambda t: t.type_tax_use == 'sale')
            else:
                tax_ids = Tax.browse()
            if not tax_ids and self.display_type == 'product':
                tax_ids = company.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda t: t.company_id == company)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids.filtered(lambda t: t.type_tax_use == 'purchase')
            else:
                tax_ids = Tax.browse()
            if not tax_ids and self.display_type == 'product':
                tax_ids = company.account_purchase_tax_id
        else:
            tax_ids = self.account_id.tax_ids

        if company and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == company)
        return tax_ids

    def _get_computed_taxes(self):
        """Devuelve el conjunto final: impuestos por defecto (producto/cuenta) mapeados por Posición Fiscal
        + impuestos extra de retención según vigencia/base (map_tax_rete). No muta self.tax_ids."""
        self.ensure_one()
        Tax = self.env['account.tax']
        company = self.move_id.company_id or self.company_id
        fp = self.move_id.fiscal_position_id
        inv_date = self.move_id.invoice_date or fields.Date.context_today(self)
        # If recompute already resolved the base for this line, use it directly.
        # This avoids using a stale base from previous line state.
        base_override = self.env.context.get('nav_base_retenciones_override')
        if base_override is not None:
            base_ret = base_override
        else:
            base_ret = self._nav_get_rete_base_for_move()

        base_tax_ids = self._nav_get_invoice_base_taxes_fresh() or Tax.browse()
        mapped_tax_ids = (self._nav_map_taxes_with_fp(fp, base_tax_ids) if fp else Tax.browse()) or Tax.browse()
        tax_ids = base_tax_ids | mapped_tax_ids
        if company:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == company)
        tax_ids = self._nav_filter_taxes_by_rules(tax_ids, inv_date, base_ret)

        if fp and (base_ret > 0.0):
            tax_ids |= fp.map_tax_rete(
                journal=self.move_id.journal_id,
                partner=self.move_id.partner_id,
                base_retenciones=base_ret,
                fecha=inv_date,
                product=self.product_id,
            )

        return tax_ids.filtered(lambda tax: tax.company_id == company) if company else tax_ids


class ResCompany(models.Model):
    _inherit = 'res.company'

    nav_rete_use_global_applicable_base = fields.Boolean(
        string="Usar base global aplicable para retención",
        default=False,
        help="Si se activa, el umbral de retención se evalúa con la suma de líneas de producto aplicables.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nav_rete_use_global_applicable_base = fields.Boolean(
        related='company_id.nav_rete_use_global_applicable_base',
        readonly=False,
        string="Usar base global aplicable para retención",
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    nav_rete_is_applicable = fields.Boolean(
        string="Aplica al umbral de retención",
        default=True,
        help="Si se activa, este producto aporta a la base global para el umbral de retención.",
    )
