from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def l10n_co_dian_get_extra_invoice_report_values(self):
        self.ensure_one()

        if self.l10n_co_edi_cufe_cude_ref:
            dian_values = self._l10n_co_dian_get_extra_invoice_report_values()
            dian_values["resolution"] = self.journal_id.l10n_co_edi_dian_authorization_number
            dian_values["invoice_name"] = self.name
            return dian_values
        return False