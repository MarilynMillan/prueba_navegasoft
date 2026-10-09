from odoo import api, fields, models
from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super()._create_account_move(balancing_account,  amount_to_balance, bank_payment_method_diffs)
        if self.config_id.analytic_account_id:
            for move in self._get_related_account_moves():
                for rec in move.line_ids:
                    income_expense_account_ids = self.env['account.account'].sudo().search(eval(ACCOUNT_DOMAIN))
                    if rec.account_id in income_expense_account_ids:
                        rec.write({
                            'analytic_distribution': {
                                self.config_id.analytic_account_id.id: 100
                            }
                        })
        return res
