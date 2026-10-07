# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    remarks_for_mrp = fields.Text(string="Remarks for MRP",)
    is_remarks_for_mrp = fields.Boolean(
        related="company_id.remark_for_mrp_production", string="Is Remarks for MRP")

    def write(self, vals):
        base_vals = dict(vals)

        # Respect explicit values passed by caller.
        if "date" in base_vals or "remarks_for_mrp" in base_vals:
            return super().write(base_vals)

        # Fast path: no company with this feature enabled.
        moves_with_backdate = self.filtered("company_id.enable_backdate_for_mrp")
        if not moves_with_backdate:
            return super().write(base_vals)

        # Group records by the effective backdate/remarks to avoid per-record writes.
        grouped_records = {}
        passthrough_records = self.browse()
        for rec in self:
            if not rec.company_id.enable_backdate_for_mrp:
                passthrough_records |= rec
                continue

            source = rec.raw_material_production_id or rec.production_id or rec.created_production_id
            if not source:
                passthrough_records |= rec
                continue

            key = (source.date_start, source.remarks)
            grouped_records.setdefault(key, self.browse())
            grouped_records[key] |= rec

        res = True
        if passthrough_records:
            res = bool(super(StockMove, passthrough_records).write(base_vals)) and res

        for (date_start, remarks), records in grouped_records.items():
            merged_vals = dict(base_vals, date=date_start, remarks_for_mrp=remarks)
            res = bool(super(StockMove, records).write(merged_vals)) and res

        return res

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()

        move_lines = self._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description)
        date = self._context.get(
            'force_period_date', fields.Date.context_today(self))
        return {
            'journal_id': journal_id,
            'line_ids': move_lines,
            'date': self.date,
            'ref': description,
            'stock_move_id': self.id,
            'stock_valuation_layer_ids': [(6, None, [svl_id])],
            'move_type': 'entry',

        }
