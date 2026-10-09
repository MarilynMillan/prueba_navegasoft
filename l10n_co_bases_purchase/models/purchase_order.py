from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _l10n_co_line_taxes(self):
        self.ensure_one()
        if "tax_ids" in self._fields:
            return self.tax_ids
        if "taxes_id" in self._fields:
            return self.taxes_id
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
