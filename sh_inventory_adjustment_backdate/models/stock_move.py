# -*- coding: utf-8 -*-
# Part of Softhealer Technologies

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    remarks_for_inventory_adj = fields.Text(
        string="Remarks for Inventory Adjustment")

    def _check_stock_account_installed(self):
        return bool(self.env.registry.get('stock.valuation.layer'))

    # FOR BACKDATE INVENTORY ADJUSTMENT

    def _action_done(self,cancel_backorder=False):
        """
        The function `_action_done` performs backdating of account moves and stock valuation layers
        based on the context provided.
        """
        backdate = self.env.context.get('sh_backdate')
        res = super()._action_done(cancel_backorder)

        if not backdate:
            return res

        backdate_remark = self.env.context.get('sh_backdate_remark')
        affected_moves = (res | self) if res else self

        affected_moves.write({
            "date": backdate,
            "remarks_for_inventory_adj": backdate_remark
        })
        if affected_moves:
            self.env.cr.execute(
                """
                UPDATE stock_move_line
                SET date = %s
                WHERE move_id IN %s
                """,
                (backdate, tuple(affected_moves.ids)),
            )
        if self._check_stock_account_installed():
            account_moves = self.env['account.move'].search(
                [('stock_move_id', 'in', affected_moves.ids)])
            if account_moves:
                account_moves.button_draft()
                account_moves.write({
                    'name': False,
                    'date': backdate,
                })
                account_moves.action_post()
            self.env.cr.execute(
                """
                UPDATE stock_valuation_layer
                SET create_date = %s
                WHERE stock_move_id IN %s
                """,
                (backdate, tuple(affected_moves.ids)),
            )
        return res
