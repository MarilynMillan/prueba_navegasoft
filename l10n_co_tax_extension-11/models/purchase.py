# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.fields import Date
from datetime import datetime
from .utils import (
    nav_get_threshold_tax_ids,
    nav_line_stable_key,
    nav_merge_preserving_non_threshold,
    nav_unique_tax_recordset,
)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id_recompute_taxes(self):
        """
        Al cambiar la Posición Fiscal, recalcula impuestos por línea desde CERO:
        - Impuestos base frescos (del producto) mapeados por FP
        - + retenciones vigentes según la base (sin arrastrar retenciones viejas)
        """
        for order in self:
            order._recompute_all_line_taxes()

    @api.onchange('order_line')
    def _onchange_order_line_structure_recompute_taxes(self):
        for order in self:
            order._recompute_all_line_taxes()

    def _recompute_all_line_taxes(self):
        for order in self:
            fp = order.fiscal_position_id
            global_applicable_base = order._get_global_applicable_rete_base()
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, order.company_id)
            if not order.order_line:
                continue

            for line in order.order_line:
                if getattr(line, 'display_type', False) in ('line_section', 'line_note'):
                    line.taxes_id = [(6, 0, [])]
                    continue
                if line.nav_disable_rete_base_calc_line:
                    continue

                taxes = line._compute_base_plus_retenciones(
                    fp=fp,
                    global_applicable_base=global_applicable_base,
                )
                computed_taxes = nav_unique_tax_recordset(taxes)
                previous_taxes = nav_unique_tax_recordset(line.taxes_id)
                include_product_taxes = (
                    not line.nav_manual_tax_override
                    and not (line._origin and line._origin.id)
                )
                line.with_context(nav_skip_manual_mark=True).taxes_id = [(6, 0, nav_merge_preserving_non_threshold(
                    previous_taxes,
                    computed_taxes,
                    threshold_tax_ids,
                    include_computed_non_threshold=include_product_taxes,
                ).ids)]

    def _get_global_applicable_rete_base(self):
        self.ensure_one()
        if not self.company_id.nav_rete_use_global_applicable_base:
            return 0.0
        total = 0.0
        for line in self.order_line:
            if getattr(line, 'display_type', False) in ('line_section', 'line_note'):
                continue
            line_base = line._get_rete_base_immediate()
            if line_base < 0.0:
                total += line_base
                continue
            if line.product_id and not line.product_id.product_tmpl_id.nav_rete_is_applicable:
                continue
            total += line_base
        return total


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    base_retenciones = fields.Float(string="Base retenciones", default=0.0)
    nav_disable_rete_base_calc_line = fields.Boolean(
        string="Deshabilitar cálculo de bases de retención",
        default=False,
    )
    nav_manual_tax_override = fields.Boolean(
        string="Edición manual de impuestos",
        default=False,
        copy=False,
    )
    @api.onchange('taxes_id')
    def _onchange_mark_manual_tax_override(self):
        if self.env.context.get('nav_skip_manual_mark'):
            return
        for line in self:
            if getattr(line, 'display_type', False) in ('line_section', 'line_note'):
                continue
            if not line.product_id and not line.taxes_id:
                continue
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, line.order_id.company_id)
            current_taxes = nav_unique_tax_recordset(line.taxes_id)
            computed_taxes = nav_unique_tax_recordset(
                line._compute_base_plus_retenciones(
                    fp=line.order_id.fiscal_position_id,
                    global_applicable_base=line.order_id._get_global_applicable_rete_base(),
                )
            )
            current_non_threshold = set(current_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            computed_non_threshold = set(computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            if current_non_threshold == computed_non_threshold:
                continue
            line.nav_manual_tax_override = True

    # -------------------------
    # COMPUTE / ONCHANGE
    # -------------------------
    @api.depends(
        'product_id', 'company_id',
        'order_id.partner_id', 'order_id.date_order',
        'order_id.company_id', 'order_id.fiscal_position_id',
        'base_retenciones',
        'price_unit', 'product_qty',
        # 'discount'  # ojo: en purchase a veces no existe; lo manejamos por getattr()
    )
    def _compute_tax_id(self):
        """
        Recalcula taxes_id desde cero (base producto mapeada por FP + retenciones).
        Evita que, al bajar la base, se queden retenciones anteriores "pegadas".
        """
        existing_by_line = {nav_line_stable_key(line): line.taxes_id for line in self}
        threshold_by_order = {
            order.id: nav_get_threshold_tax_ids(self.env, order.company_id)
            for order in self.mapped('order_id')
        }
        for line in self:
            if line.nav_manual_tax_override or line.nav_disable_rete_base_calc_line:
                continue
            if getattr(line, 'display_type', False) in ('line_section', 'line_note'):
                continue
            if not (line._origin and line._origin.id):
                continue
            threshold_tax_ids = threshold_by_order.get(line.order_id.id, set())
            current_taxes = nav_unique_tax_recordset(line.taxes_id)
            computed_taxes = nav_unique_tax_recordset(
                line._compute_base_plus_retenciones(
                    fp=line.order_id.fiscal_position_id,
                    global_applicable_base=line.order_id._get_global_applicable_rete_base(),
                )
            )
            current_non_threshold = set(current_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            computed_non_threshold = set(computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            if current_non_threshold != computed_non_threshold:
                line.nav_manual_tax_override = True
        unlocked_lines = self.filtered(
            lambda l: not l.nav_disable_rete_base_calc_line and not l.nav_manual_tax_override
        )
        if unlocked_lines:
            super(PurchaseOrderLine, unlocked_lines)._compute_tax_id()
        global_orders = self.mapped('order_id').filtered(
            lambda o: o.company_id.nav_rete_use_global_applicable_base
        )
        if global_orders:
            global_orders._recompute_all_line_taxes()
        for line in self:
            if line.nav_disable_rete_base_calc_line:
                previous_taxes = existing_by_line.get(nav_line_stable_key(line))
                if previous_taxes is not None:
                    line.taxes_id = [(6, 0, nav_unique_tax_recordset(previous_taxes).ids)]
                continue
            if line.order_id in global_orders:
                continue
            if getattr(line, 'display_type', False) in ('line_section', 'line_note'):
                line.taxes_id = [(6, 0, [])]
                continue

            taxes = line._compute_base_plus_retenciones(
                fp=line.order_id.fiscal_position_id,
                global_applicable_base=line.order_id._get_global_applicable_rete_base(),
            )
            computed_taxes = nav_unique_tax_recordset(taxes)
            if line._origin and line._origin.id:
                previous_taxes = existing_by_line.get(nav_line_stable_key(line))
            else:
                previous_taxes = line.taxes_id
            include_product_taxes = (
                not line.nav_manual_tax_override
                and not (line._origin and line._origin.id)
            )
            line.with_context(nav_skip_manual_mark=True).taxes_id = [(6, 0, nav_merge_preserving_non_threshold(
                nav_unique_tax_recordset(previous_taxes),
                computed_taxes,
                threshold_by_order.get(line.order_id.id, set()),
                include_computed_non_threshold=include_product_taxes,
            ).ids)]

    @api.onchange(
        'product_id', 'company_id', 'base_retenciones',
        'order_id', 'price_unit', 'product_qty',
        # 'discount'  # igual, depende de versión/módulos
    )
    def _onchange_product_or_ctx_recompute_taxes(self):
        """
        Refresco inmediato en UI:
        - base del producto (fresca) + retenciones actuales
        """
        for line in self:
            if line.nav_disable_rete_base_calc_line:
                continue
            if getattr(line, 'display_type', False) in ('line_section', 'line_note'):
                line.taxes_id = [(6, 0, [])]
                continue
            if line.order_id.company_id.nav_rete_use_global_applicable_base:
                line.order_id._recompute_all_line_taxes()
                continue

            taxes = line._compute_base_plus_retenciones(
                fp=line.order_id.fiscal_position_id,
                global_applicable_base=line.order_id._get_global_applicable_rete_base(),
            )
            computed_taxes = nav_unique_tax_recordset(taxes)
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, line.order_id.company_id)
            include_product_taxes = (
                not line.nav_manual_tax_override
                and not (line._origin and line._origin.id)
            )
            line.with_context(nav_skip_manual_mark=True).taxes_id = [(6, 0, nav_merge_preserving_non_threshold(
                nav_unique_tax_recordset(line.taxes_id),
                computed_taxes,
                threshold_tax_ids,
                include_computed_non_threshold=include_product_taxes,
            ).ids)]

    # -------------------------
    # HELPERS
    # -------------------------
    def _get_rete_base_immediate(self):
        """
        Base inmediata (estable en UI). NO depende de price_subtotal.
        En purchase: price_unit * qty * (1 - discount)
        """
        self.ensure_one()
        qty = self.product_qty or 0.0
        price = self.price_unit or 0.0
        disc = getattr(self, 'discount', 0.0) or 0.0
        disc = disc / 100.0
        return price * qty * (1.0 - disc)

    def _map_taxes_with_fp(self, fp, taxes):
        """
        Mapea impuestos con la Posición Fiscal sin asumir la firma de map_tax().
        """
        if not fp:
            return taxes

        try:
            return fp.map_tax(taxes)
        except TypeError:
            pass

        try:
            return fp.map_tax(taxes, partner=self.order_id.partner_id)
        except TypeError:
            pass

        try:
            return fp.map_tax(taxes, partner_id=self.order_id.partner_id.id)
        except TypeError:
            pass

        return taxes

    def _get_base_taxes_fresh(self, fp=None):
        """
        Impuestos BASE frescos (sin retenciones):
        - supplier_taxes_id (compra) del producto
        - filtrados por compañía/uso purchase
        - mapeados por FP mediante _map_taxes_with_fp()
        """
        self.ensure_one()
        Tax = self.env['account.tax']
        company = self.order_id.company_id

        base = (self.product_id.supplier_taxes_id or Tax.browse()).filtered(
            lambda t: t.company_id == company and t.type_tax_use in ('purchase', 'none')
        )

        if fp:
            base |= self._map_taxes_with_fp(fp, base)

        return base.filtered(
            lambda t: t.company_id == company and t.type_tax_use in ('purchase', 'none')
        )

    def _compute_base_plus_retenciones(self, fp=None, global_applicable_base=None):
        """
        Calcula impuestos finales = base fresca + retenciones vigentes.

        IMPORTANTE:
        - No usamos self.taxes_id como base (porque arrastra retenciones viejas).
        - Retenciones se calculan con base inmediata (para que funcione al crear línea nueva).
        """
        self.ensure_one()
        Tax = self.env['account.tax']
        company = self.order_id.company_id

        # 1) Base fresca (del producto)
        base_taxes = self._get_base_taxes_fresh(fp=fp)

        # 2) Retenciones según vigencia/base
        extra = Tax.browse()
        if fp:
            inv_dt = self.order_id.date_order or Date.context_today(self)
            if isinstance(inv_dt, datetime):
                inv_dt = inv_dt.date()

            if company.nav_rete_use_global_applicable_base:
                if self._get_rete_base_immediate() <= 0.0:
                    base_ret = 0.0
                elif self.product_id and not self.product_id.product_tmpl_id.nav_rete_is_applicable:
                    base_ret = 0.0
                else:
                    base_ret = global_applicable_base
                    if base_ret is None:
                        base_ret = self.order_id._get_global_applicable_rete_base()
            else:
                # ✅ Base estable:
                # - si llenas base_retenciones manualmente, gana
                # - si no, usa base calculada inmediata (NO price_subtotal)
                base_ret = self.base_retenciones or self._get_rete_base_immediate()

            # map_tax_rete SIN product (como pediste)
            if base_ret > 0.0:
                try:
                    extra = fp.map_tax_rete(
                        journal=False,
                        fecha=inv_dt,
                        partner=self.order_id.partner_id,
                        base_retenciones=base_ret,
                    )
                except TypeError:
                    extra = fp.map_tax_rete(
                        fecha=inv_dt,
                        partner=self.order_id.partner_id,
                        base_retenciones=base_ret,
                    )

        # 3) Unión final + filtro por compañía/uso
        taxes = (base_taxes | extra).filtered(
            lambda t: t.company_id == company and t.type_tax_use in ('purchase', 'none')
        )
        return taxes
