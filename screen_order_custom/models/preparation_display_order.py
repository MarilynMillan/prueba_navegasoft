from odoo import fields, models, api


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    def _export_for_ui(self, preparation_display):
        res = super(PosPreparationDisplayOrder, self)._export_for_ui(preparation_display)
        if res:
            for orderline in res.get("orderlines", []):
                orderline_obj = self.env["pos_preparation_display.orderline"].browse(
                    orderline.get("id", False)
                )
                orderline["pos_combo_list"] = orderline_obj.pos_combo_list

            # Agregar floor_name a la info de la mesa
            if res.get('table') and self.pos_order_id.table_id:
                res['table']['floor_name'] = self.pos_order_id.table_id.floor_id.name or ''

            # Agregar waiter_name
            res['waiter_name'] = self.pos_order_id.waiter_name or ''
        return res
