from odoo import api, fields, models
from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super()._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)

        analytic_account = self.config_id.analytic_account_id
        if analytic_account:
            related_moves = self._get_related_account_moves()
            if related_moves:
                income_expense_account_ids = self.env['account.account'].sudo().search(
                    eval(ACCOUNT_DOMAIN)
                ).ids
                if income_expense_account_ids:
                    target_lines = self.env['account.move.line'].sudo().search([
                        ('move_id', 'in', related_moves.ids),
                        ('account_id', 'in', income_expense_account_ids),
                    ])
                    if target_lines:
                        for line in target_lines:
                            line.write({
                                'analytic_distribution': {analytic_account.id: 100}
                            })
        return res
