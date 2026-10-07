# -*- coding: utf-8 -*-

from odoo import Command, models
from odoo.tools import OrderedSet, float_compare, float_is_zero


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _free_reservation(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, ml_ids_to_ignore=None):
        """Performance override:
        keep original behavior but force a cheap SQL order in search().
        Core immediately re-sorts candidates in Python, so default SQL order
        (which joins stock_quant_package by name) is unnecessary overhead.
        """
        self.ensure_one()
        if ml_ids_to_ignore is None:
            ml_ids_to_ignore = OrderedSet()
        ml_ids_to_ignore |= self.ids

        if self.move_id._should_bypass_reservation(location_id):
            return

        outdated_move_lines_domain = [
            ("state", "not in", ["done", "cancel"]),
            ("product_id", "=", product_id.id),
            ("lot_id", "=", lot_id.id if lot_id else False),
            ("location_id", "=", location_id.id),
            ("owner_id", "=", owner_id.id if owner_id else False),
            ("package_id", "=", package_id.id if package_id else False),
            ("quantity_product_uom", ">", 0.0),
            ("picked", "=", False),
            ("id", "not in", tuple(ml_ids_to_ignore)),
        ]

        def current_picking_first(cand):
            return (
                cand.picking_id != self.move_id.picking_id,
                -(cand.picking_id.scheduled_date or cand.move_id.date).timestamp() if cand.picking_id or cand.move_id else 0,
                -cand.id,
            )

        # Critical change: avoid default model order that joins package name.
        outdated_candidates = self.env["stock.move.line"].search(outdated_move_lines_domain, order="id")
        outdated_candidates = outdated_candidates.sorted(current_picking_first)

        move_to_reassign = self.env["stock.move"]
        to_unlink_candidate_ids = set()

        if not outdated_candidates:
            return

        rounding = self.product_uom_id.rounding
        for candidate in outdated_candidates:
            move_to_reassign |= candidate.move_id
            if float_compare(candidate.quantity_product_uom, quantity, precision_rounding=rounding) <= 0:
                quantity -= candidate.quantity_product_uom
                to_unlink_candidate_ids.add(candidate.id)
                if float_is_zero(quantity, precision_rounding=rounding):
                    break
            else:
                candidate.quantity -= candidate.product_id.uom_id._compute_quantity(
                    quantity,
                    candidate.product_uom_id,
                    rounding_method="HALF-UP",
                )
                break

        move_line_to_unlink = self.env["stock.move.line"].browse(to_unlink_candidate_ids)
        moves_to_update = move_line_to_unlink.move_id | move_to_reassign
        if moves_to_update:
            moves_to_update.write({
                "procure_method": "make_to_stock",
                "move_orig_ids": [Command.clear()],
            })
        if move_line_to_unlink:
            move_line_to_unlink.unlink()
        if move_to_reassign:
            move_to_reassign._action_assign()
