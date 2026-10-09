# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models
from .utils import (
    nav_get_threshold_tax_ids,
    nav_line_stable_key,
    nav_merge_preserving_non_threshold,
    nav_unique_tax_recordset,
)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        # Mantengo tu lógica de forzar date en el invoice
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals["date"] = fields.Date.context_today(self)
        return invoice_vals

    @api.onchange("fiscal_position_id")
    def _onchange_fiscal_position_id_recompute_taxes(self):
        """Al cambiar la posición fiscal del pedido, recomputa impuestos de todas las líneas (UI inmediato)."""
        for order in self:
            order._recompute_all_line_taxes()

    @api.onchange("order_line")
    def _onchange_order_line_structure_recompute_taxes(self):
        for order in self:
            if order.company_id.nav_rete_use_global_applicable_base:
                order._recompute_all_line_taxes()
                continue
            origin_count = len(order._origin.order_line) if order._origin else 0
            current_count = len(order.order_line)
            if current_count != origin_count:
                order._recompute_all_line_taxes()

    def _recompute_all_line_taxes(self):
        for order in self:
            fp = order.fiscal_position_id
            global_applicable_base = order._get_global_applicable_rete_base()
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, order.company_id)
            for line in order.order_line.filtered(lambda l: l.display_type not in ("line_section", "line_note")):
                if line.nav_disable_rete_base_calc_line:
                    continue
                computed_taxes = nav_unique_tax_recordset(line._get_order_computed_taxes(
                    fp=fp,
                    global_applicable_base=global_applicable_base,
                ))
                previous_taxes = nav_unique_tax_recordset(line.tax_id)
                include_product_taxes = (
                    not line.nav_manual_tax_override
                    and not (line._origin and line._origin.id)
                )
                line.with_context(nav_skip_manual_mark=True).tax_id = nav_merge_preserving_non_threshold(
                    previous_taxes,
                    computed_taxes,
                    threshold_tax_ids,
                    include_computed_non_threshold=include_product_taxes,
                )

    def _get_global_applicable_rete_base(self):
        self.ensure_one()
        if not self.company_id.nav_rete_use_global_applicable_base:
            return 0.0
        total = 0.0
        for line in self.order_line:
            if line.display_type in ("line_section", "line_note"):
                continue
            line_base = line._get_rete_base_immediate()
            if line_base <= 0.0:
                continue
            if line.product_id and not line.product_id.product_tmpl_id.nav_rete_is_applicable:
                continue
            total += line_base
        return total


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Campo auxiliar para retenciones (si lo llenas manualmente, se prioriza)
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
    @api.onchange("tax_id")
    def _onchange_mark_manual_tax_override(self):
        if self.env.context.get("nav_skip_manual_mark"):
            return
        for line in self:
            if line.display_type in ("line_section", "line_note"):
                continue
            if not line.product_id and not line.tax_id:
                continue
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, line.order_id.company_id)
            current_taxes = nav_unique_tax_recordset(line.tax_id)
            computed_taxes = nav_unique_tax_recordset(
                line._get_order_computed_taxes(fp=line.order_id.fiscal_position_id)
            )
            current_non_threshold = set(current_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            computed_non_threshold = set(computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            if current_non_threshold == computed_non_threshold:
                continue
            line.nav_manual_tax_override = True

    # -----------------------------
    # Helpers
    # -----------------------------
    def _get_rete_base_immediate(self):
        """Base inmediata (estable en UI). NO depende de price_subtotal."""
        self.ensure_one()
        qty = self.product_uom_qty or 0.0
        disc = (self.discount or 0.0) / 100.0
        return (self.price_unit or 0.0) * qty * (1.0 - disc)

    # -----------------------------
    # Compute nativo + override final
    # -----------------------------
    @api.depends(
        "product_id",
        "company_id",
        "order_id.partner_id",
        "order_id.partner_shipping_id",
        "order_id.company_id",
        "order_id.fiscal_position_id",
        "base_retenciones",
        "price_unit",
        "product_uom_qty",
        "discount",
    )
    def _compute_tax_id(self):
        """
        1) Llama primero la lógica nativa para mantener comportamiento estándar.
        2) Aplica mapeo estándar por Posición Fiscal.
        3) Suma impuestos extra de retención (map_tax_rete), ADITIVOS.
        """
        existing_by_line = {nav_line_stable_key(line): line.tax_id for line in self}
        threshold_by_order = {
            order.id: nav_get_threshold_tax_ids(self.env, order.company_id)
            for order in self.mapped("order_id")
        }
        for line in self:
            if line.nav_manual_tax_override or line.nav_disable_rete_base_calc_line:
                continue
            if line.display_type in ("line_section", "line_note"):
                continue
            if not (line._origin and line._origin.id):
                continue
            threshold_tax_ids = threshold_by_order.get(line.order_id.id, set())
            current_taxes = nav_unique_tax_recordset(line.tax_id)
            computed_taxes = nav_unique_tax_recordset(
                line._get_order_computed_taxes(fp=line.order_id.fiscal_position_id)
            )
            current_non_threshold = set(current_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            computed_non_threshold = set(computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids).ids)
            if current_non_threshold != computed_non_threshold:
                line.nav_manual_tax_override = True
        unlocked_lines = self.filtered(
            lambda l: not l.nav_disable_rete_base_calc_line and not l.nav_manual_tax_override
        )
        if unlocked_lines:
            super(SaleOrderLine, unlocked_lines)._compute_tax_id()

        global_orders = self.mapped("order_id").filtered(
            lambda o: o.company_id.nav_rete_use_global_applicable_base
        )
        if global_orders:
            global_orders._recompute_all_line_taxes()
        for line in self:
            if line.nav_disable_rete_base_calc_line:
                previous_taxes = existing_by_line.get(nav_line_stable_key(line))
                if previous_taxes is not None:
                    line.tax_id = nav_unique_tax_recordset(previous_taxes)
                continue
            if line.order_id in global_orders:
                continue
            if line.display_type in ("line_section", "line_note"):
                continue
            fp = line.order_id.fiscal_position_id
            computed_taxes = nav_unique_tax_recordset(line._get_order_computed_taxes(fp=fp))
            if line._origin and line._origin.id:
                previous_taxes = existing_by_line.get(nav_line_stable_key(line))
            else:
                previous_taxes = line.tax_id
            include_product_taxes = (
                not line.nav_manual_tax_override
                and not (line._origin and line._origin.id)
            )
            line.with_context(nav_skip_manual_mark=True).tax_id = nav_merge_preserving_non_threshold(
                nav_unique_tax_recordset(previous_taxes),
                computed_taxes,
                threshold_by_order.get(line.order_id.id, set()),
                include_computed_non_threshold=include_product_taxes,
            )

    # -----------------------------
    # Onchange para UI inmediata
    # -----------------------------
    @api.onchange("product_id", "price_unit", "product_uom_qty", "discount")
    def _onchange_recompute_taxes_ui(self):
        """
        Garantiza que al crear una línea (qty=1, price_unit auto) se asignen impuestos de inmediato,
        sin necesidad de “tocar” el precio luego.
        """
        for line in self:
            if line.nav_disable_rete_base_calc_line:
                continue
            if line.display_type in ("line_section", "line_note"):
                continue
            if line.order_id.company_id.nav_rete_use_global_applicable_base:
                line.order_id._recompute_all_line_taxes()
                continue
            fp = line.order_id.fiscal_position_id
            global_applicable_base = line.order_id._get_global_applicable_rete_base()
            computed_taxes = nav_unique_tax_recordset(line._get_order_computed_taxes(
                fp=fp,
                global_applicable_base=global_applicable_base,
            ))
            threshold_tax_ids = nav_get_threshold_tax_ids(self.env, line.order_id.company_id)
            include_product_taxes = (
                not line.nav_manual_tax_override
                and not (line._origin and line._origin.id)
            )
            line.with_context(nav_skip_manual_mark=True).tax_id = nav_merge_preserving_non_threshold(
                nav_unique_tax_recordset(line.tax_id),
                computed_taxes,
                threshold_tax_ids,
                include_computed_non_threshold=include_product_taxes,
            )

    @api.onchange("price_unit", "product_uom_qty", "discount", "product_id")
    def _onchange_recompute_global_threshold(self):
        orders = self.mapped("order_id").filtered(lambda o: o.company_id.nav_rete_use_global_applicable_base)
        for order in orders:
            order._recompute_all_line_taxes()

    # ---- Helper específico para Sale ----
    def _get_order_computed_taxes(self, fp=None, global_applicable_base=None):
        """
        Devuelve impuestos finales para la línea de venta:
        - Impuestos base por producto (uso 'sale'), filtrados por compañía
        - Mapeo estándar por posición fiscal
        - Unión con impuestos extra (retenciones) devueltos por map_tax_rete
        """
        self.ensure_one()
        Tax = self.env["account.tax"]
        company = self.order_id.company_id

        # 1) impuestos base por producto (venta)
        if self.product_id and self.product_id.taxes_id:
            tax_ids = self.product_id.taxes_id.filtered(
                lambda t: t.company_id == company and (t.type_tax_use in ("sale", "none"))
            )
        else:
            tax_ids = company.account_sale_tax_id or Tax.browse()

        # 2) mapeo estándar por posición fiscal
        if fp and tax_ids:
            tax_ids |= fp.map_tax(tax_ids)

        # 3) fecha efectiva
        inv_date = self.order_id.date_order or fields.Date.context_today(self)
        if isinstance(inv_date, datetime):
            inv_date = inv_date.date()

        # 4) base para retenciones
        if company.nav_rete_use_global_applicable_base:
            if self._get_rete_base_immediate() <= 0.0:
                base_for_rete = 0.0
            elif self.product_id and not self.product_id.product_tmpl_id.nav_rete_is_applicable:
                base_for_rete = 0.0
            else:
                base_for_rete = global_applicable_base
                if base_for_rete is None:
                    base_for_rete = self.order_id._get_global_applicable_rete_base()
        else:
            base_for_rete = self.base_retenciones or self._get_rete_base_immediate()

        extra = Tax.browse()
        if fp and (base_for_rete > 0.0):
            extra = fp.map_tax_rete(
                journal=False,  # En pedido no hay diario
                fecha=inv_date,
                product=self.product_id,
                partner=self.order_id.partner_id,
                base_retenciones=base_for_rete,
            )

        # 5) unión y filtrado por compañía/uso venta
        taxes = (tax_ids | extra).filtered(
            lambda t: t.company_id == company and (t.type_tax_use in ("sale", "none"))
        )
        return taxes
