from odoo import api, fields, models
from odoo.exceptions import UserError


class InvoiceLineGrouped(models.TransientModel):
    _name = "invoice.line.grouped"
    _description = "Invoice Line Grouped"

    name = fields.Char()
    price_subtotal = fields.Monetary(currency_field="currency_id")
    price_total = fields.Monetary(currency_field="currency_id")
    price_unit = fields.Monetary(currency_field="currency_id")
    quantity = fields.Float()
    discount = fields.Float()
    product_uom_id = fields.Many2one("uom.uom")
    product_id = fields.Many2one("product.product")
    display_type = fields.Char()
    collapse_prices = fields.Boolean(default=False)
    collapse_composition = fields.Boolean(default=False)
    tax_ids = fields.Many2many("account.tax")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    def _nav_line_taxes_print(self):
        self.ensure_one()
        labels = []
        for tax in self.tax_ids:
            label = tax.invoice_label or tax.name or ""
            if label and label not in labels:
                labels.append(label)
        return ", ".join(labels)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _nav_is_groupable_for_dian(self):
        self.ensure_one()
        return bool(
            self.move_id.move_type == "out_invoice"
            and self.product_id
            and self.display_type in (False, "product")
        )

    def _nav_grouped_product_for_dian(self):
        self.ensure_one()
        mode = self.move_id.company_id.dian_grouping_product_mode or "variant"
        if mode == "template":
            return self.product_id.product_tmpl_id.product_variant_id
        return self.product_id

    def _nav_grouped_product_ref_for_dian(self):
        self.ensure_one()
        mode = self.move_id.company_id.dian_grouping_product_mode or "variant"
        if mode == "template":
            return ("template", self.product_id.product_tmpl_id.id or 0)
        return ("variant", self.product_id.id or 0)

    def _nav_grouped_product_id_for_dian(self):
        self.ensure_one()
        mode = self.move_id.company_id.dian_grouping_product_mode or "variant"
        if mode == "template":
            return -(self.product_id.product_tmpl_id.id or 0)
        return self.product_id.id or 0

    def _nav_grouping_key_for_dian(self):
        self.ensure_one()
        product = self._nav_grouped_product_for_dian()
        return (
            self._nav_grouped_product_ref_for_dian(),
            tuple(sorted(self.tax_ids.ids)),
            round((self.discount or 0.0), 6),
            self.product_uom_id.id or 0,
        )

    def _nav_grouped_display_name_for_dian(self):
        self.ensure_one()
        product = self._nav_grouped_product_for_dian()
        if not product:
            return self.name
        if product.default_code:
            return f"[{product.default_code}] {product.name}"
        return product.name or self.name


class AccountMove(models.Model):
    _inherit = "account.move"

    total_grouped_lines_by_variant = fields.Integer(
        compute="_compute_total_grouped_lines_by_variant",
    )
    dian_grouping_active = fields.Boolean(compute="_compute_dian_grouping_active")

    def _get_grouped_lines_limit(self):
        return int(
            self.env["ir.config_parameter"].sudo().get_param(
                "dian_account_move_line_restriction.grouped_lines_limit",
                default=100,
            )
        )

    def _is_dian_grouping_active(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return False
        scope = self.company_id.dian_grouping_scope or "global"
        if scope == "global":
            return True
        return bool(
            self.journal_id
            and self.journal_id in self.company_id.dian_grouping_journal_ids
        )

    @api.depends(
        "move_type",
        "journal_id",
        "company_id",
        "company_id.dian_grouping_scope",
        "company_id.dian_grouping_journal_ids",
    )
    def _compute_dian_grouping_active(self):
        for move in self:
            move.dian_grouping_active = move._is_dian_grouping_active()

    @api.depends(
        "move_type",
        "invoice_line_ids.display_type",
        "invoice_line_ids.product_id",
        "invoice_line_ids.product_id.product_tmpl_id",
        "invoice_line_ids.tax_ids",
        "invoice_line_ids.discount",
        "invoice_line_ids.product_uom_id",
        "company_id.dian_grouping_product_mode",
    )
    def _compute_total_grouped_lines_by_variant(self):
        for move in self:
            if not move._is_dian_grouping_active():
                move.total_grouped_lines_by_variant = 0
                continue
            move.total_grouped_lines_by_variant = len(move._nav_grouping_keys_for_dian())

    def _nav_grouping_keys_for_dian(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return set()
        return {
            line._nav_grouping_key_for_dian()
            for line in self.invoice_line_ids
            if line._nav_is_groupable_for_dian()
        }

    def _nav_check_grouped_line_limit_for_dian(self):
        self.ensure_one()
        grouped_lines_limit = self._get_grouped_lines_limit()
        if self._is_dian_grouping_active() and self.total_grouped_lines_by_variant > grouped_lines_limit:
            raise UserError(
                "The invoice has more than %(limit)s grouped product combinations. "
                "Please reduce the number of grouped invoice lines before printing or sending."
                % {"limit": grouped_lines_limit}
            )

    def action_print_pdf(self):
        for move in self:
            move._nav_check_grouped_line_limit_for_dian()
        return super().action_print_pdf()

    def action_invoice_sent(self):
        for move in self:
            move._nav_check_grouped_line_limit_for_dian()
        return super().action_invoice_sent()

    def _nav_get_grouped_invoice_lines_for_pdf(self, grouped_model):
        self.ensure_one()
        sorted_lines = self.invoice_line_ids.sorted(
            key=lambda line: (
                -line.sequence,
                line.date,
                line.move_name,
                -(line._origin.id or (line.id if isinstance(line.id, int) else 0)),
            ),
            reverse=True,
        )
        if self.move_type != "out_invoice":
            return sorted_lines
        if not self._is_dian_grouping_active():
            return sorted_lines

        grouped_lines = {}
        grouped_meta = {}
        output_lines = []

        for line in sorted_lines:
            if not line._nav_is_groupable_for_dian():
                output_lines.append(line)
                continue

            grouping_key = line._nav_grouping_key_for_dian()
            gross_total = line.price_unit * line.quantity
            grouped_line = grouped_lines.get(grouping_key)
            grouped_product = line._nav_grouped_product_for_dian()

            if not grouped_line:
                grouped_line = grouped_model.new({
                    "price_subtotal": line.price_subtotal,
                    "price_total": line.price_total,
                    "display_type": line.display_type,
                    "name": line._nav_grouped_display_name_for_dian(),
                    "quantity": line.quantity,
                    "product_id": grouped_product.id if grouped_product else False,
                    "product_uom_id": line.product_uom_id.id,
                    "price_unit": line.price_unit,
                    "discount": line.discount,
                    "tax_ids": [(6, 0, line.tax_ids.ids)],
                    "currency_id": line.currency_id.id,
                })
                grouped_lines[grouping_key] = grouped_line
                grouped_meta[grouping_key] = {"gross_total": gross_total}
                output_lines.append(grouped_line)
                continue

            grouped_line.quantity += line.quantity
            grouped_line.price_subtotal += line.price_subtotal
            grouped_line.price_total += line.price_total
            grouped_meta[grouping_key]["gross_total"] += gross_total
            grouped_line.price_unit = (
                grouped_meta[grouping_key]["gross_total"] / grouped_line.quantity
                if grouped_line.quantity
                else 0.0
            )

        return output_lines
