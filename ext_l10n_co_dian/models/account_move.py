from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code', 'company_currency_id', 'move_type', 'company_id.l10n_co_dian_provider')
    def _compute_l10n_co_dian_is_enabled(self):
        super()._compute_l10n_co_dian_is_enabled()
        for move in self:
            if move.amount_total == 0:
                move.l10n_co_dian_is_enabled = False
