from odoo import api, models


def get_invoice_grouped_lines(report_values, orm):
    grouped_model = orm.env["invoice.line.grouped"]
    report_values["invoices_grouped"] = {
        move.id: move._nav_get_grouped_invoice_lines_for_pdf(grouped_model)
        for move in report_values.get("docs", [])
    }
    return report_values


class ReportInvoiceWithoutPayment(models.AbstractModel):
    _inherit = "report.account.report_invoice"

    @api.model
    def _get_report_values(self, docids, data=None):
        return get_invoice_grouped_lines(super()._get_report_values(docids, data), self)


class ReportAccountReportInvoiceWithPayments(models.AbstractModel):
    _inherit = "report.account.report_invoice_with_payments"

    @api.model
    def _get_report_values(self, docids, data=None):
        return get_invoice_grouped_lines(super()._get_report_values(docids, data), self)
