from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_attachment_domains(self):
        # Enterprise account_accountant can call this method on multi-recordsets.
        # Keep singleton behavior for 1 record and provide a safe multi fallback.
        if len(self) == 1:
            return super()._get_attachment_domains()

        domains = [[
            ("res_model", "=", "account.move"),
            ("res_id", "in", self.mapped("move_id").ids),
            ("res_field", "in", (False, "invoice_pdf_report_file")),
        ]]

        statement_ids = self.mapped("statement_id").ids
        if statement_ids:
            domains.append([
                ("res_model", "=", "account.bank.statement"),
                ("res_id", "in", statement_ids),
            ])

        payment_ids = self.mapped("payment_id").ids
        if payment_ids:
            domains.append([
                ("res_model", "=", "account.payment"),
                ("res_id", "in", payment_ids),
            ])

        return domains

    def _get_attachment_by_record(self, id_model2attachments, move_line):
        return (
            id_model2attachments.get(("account.move", move_line.move_id.id))
            or id_model2attachments.get(("account.bank.statement", move_line.statement_id.id))
            or id_model2attachments.get(("account.payment", move_line.payment_id.id))
        )
