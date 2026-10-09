# -*- coding: utf-8 -*-
# Part of Softhealer Technologies

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    remarks_for_inventory_adj = fields.Text(
        string="Remarks for Inventory Adjustment")

    def _check_stock_account_installed(self):
        account_app = self.env['ir.module.module'].sudo().search([('name','=','stock_account')],limit=1)
        if account_app.state != 'installed':
            return False
        else:
            return True

    # FOR BACKDATE INVENTORY ADJUSTMENT

    def _action_done(self,cancel_backorder=False):
        """
        The function `_action_done` performs backdating of account moves and stock valuation layers
        based on the context provided.
        """
        res = super()._action_done(cancel_backorder)
        backdate = self.env.context.get('sh_backdate')
        if backdate:
            backdate_remark = self.env.context.get('sh_backdate_remark')
            self.write({
                "date": backdate,
                "remarks_for_inventory_adj": backdate_remark
            })
            self.move_line_ids.date = backdate
            if self._check_stock_account_installed():
                account_moves = self.env['account.move'].search(
                    [('stock_move_id', 'in', (res|self).ids)])
                account_moves.button_draft()
                account_moves.name = False
                account_moves.date = backdate
                account_moves.action_post()
                self.env.cr.execute("""
                        Update stock_valuation_layer set create_date=%s where stock_move_id in %s; 
                    """, (backdate, tuple(self.ids)))
        return res
