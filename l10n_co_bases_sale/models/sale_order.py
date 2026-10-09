from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _l10n_co_line_taxes(self):
        self.ensure_one()
        if "tax_ids" in self._fields:
            return self.tax_ids
        if "tax_id" in self._fields:
            return self.tax_id
        return self.env["account.tax"]

    def _l10n_co_line_taxes_print(self):
        self.ensure_one()
        labels = []
        for tax in self._l10n_co_line_taxes():
            if tax.notprintable:
                continue
            label = (
                getattr(tax, "tax_label", False)
                or getattr(tax, "invoice_label", False)
                or tax.name
                or ""
            )
            if label and label not in labels:
                labels.append(label)
        return ", ".join(labels)

    def _l10n_co_has_printable_taxes(self):
        self.ensure_one()
        return bool(self._l10n_co_line_taxes().filtered(lambda tax: not tax.notprintable))

    def _get_grouped_section_summary(self, display_taxes=True):
        summary = super()._get_grouped_section_summary(display_taxes=display_taxes)
        if not display_taxes:
            return summary

        hidden_labels = set()
        for line in self.order_id.order_line:
            for tax in line._l10n_co_line_taxes().filtered("notprintable"):
                label = (
                    getattr(tax, "tax_label", False)
                    or getattr(tax, "invoice_label", False)
                    or tax.name
                    or ""
                )
                if label:
                    hidden_labels.add(label)

        for section_line in summary:
            section_line["tax_labels"] = [
                label
                for label in section_line.get("tax_labels", [])
                if label not in hidden_labels
            ]
        return summary
