import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    # =====================================================================
    # OVERRIDE: process_order - excluir pantallas waiter
    # =====================================================================
    @api.model
    def process_order(self, order_id, cancelled=False, general_note=False, note_history=False):
        """Override: las pantallas tipo waiter NO reciben órdenes del POS.
        Solo reciben cuando cocina marca 'Listo' (via change_order_stage).
        """
        order = self.env['pos.order'].browse(order_id)
        if not order:
            return

        data = order._process_preparation_changes(cancelled, general_note, note_history)

        preparation_displays = self.env['pos_preparation_display.display'].search([
            '&',
            '|', ('pos_config_ids', '=', False),
            ('pos_config_ids', 'in', [order.config_id.id]),
            '|', ('category_ids', 'in', list(data['category_ids'])),
            ('category_ids', '=', False)
        ])

        preparation_displays = preparation_displays.filtered(
            lambda d: d.display_type != 'waiter'
        )

        if data['change']:
            for p_dis in preparation_displays:
                p_dis._send_load_orders_message(data['sound'])
        return True

    # =====================================================================
    # OVERRIDE: change_order_stage - EL PUENTE (kitchen → waiter)
    # =====================================================================
    def change_order_stage(self, stage_id, preparation_display_id):
        """Override: cuando una orden llega a la última etapa de una pantalla
        kitchen, propaga a las pantallas waiter vinculadas.
        """
        result = super().change_order_stage(stage_id, preparation_display_id)

        source_display = self.env['pos_preparation_display.display'].browse(
            preparation_display_id
        )

        if source_display.display_type != 'kitchen':
            return result

        if not source_display.stage_ids:
            return result
        last_stage_id = source_display.stage_ids[-1].id
        if stage_id != last_stage_id:
            return result

        waiter_displays = self.env['pos_preparation_display.display'].search([
            ('display_type', '=', 'waiter'),
            ('source_category_ids.source_display_id', '=', source_display.id),
        ])

        if not waiter_displays:
            return result

        pos_config_id = self.pos_order_id.config_id.id if self.pos_order_id else False
        if pos_config_id:
            waiter_displays = waiter_displays.filtered(
                lambda d: not d.pos_config_ids or pos_config_id in d.pos_config_ids.ids
            )

        if not waiter_displays:
            return result

        for waiter_display in waiter_displays:
            try:
                self._propagate_to_waiter(waiter_display, source_display)
            except Exception as e:
                _logger.error(
                    "Error propagando orden %s a pantalla waiter %s: %s",
                    self.id, waiter_display.id, str(e)
                )

        return result

    def _propagate_to_waiter(self, waiter_display, source_display):
        """Crea un nuevo order.stage en la primera etapa de meseros."""
        source_config = waiter_display.source_category_ids.filtered(
            lambda sc: sc.source_display_id.id == source_display.id
        )
        if not source_config:
            return

        allowed_cats = set(source_config.category_ids.ids)
        has_relevant_lines = False
        for line in self.preparation_display_order_line_ids:
            line_cats = set(line.product_id.pos_categ_ids.ids)
            if line_cats & allowed_cats:
                has_relevant_lines = True
                break

        if not has_relevant_lines:
            return

        first_stage = waiter_display.stage_ids[0] if waiter_display.stage_ids else False
        if not first_stage:
            return

        self.env['pos_preparation_display.order.stage'].create({
            'preparation_display_id': waiter_display.id,
            'stage_id': first_stage.id,
            'order_id': self.id,
            'done': False,
        })

        waiter_display._notify('LOAD_ORDERS', {'sound': True})

    # =====================================================================
    # OVERRIDE: _export_for_ui
    # =====================================================================
    def _export_for_ui(self, preparation_display):
        """Override:
        - waiter: super() directo
        - kitchen con config v1: pasa pos_config_id por contexto
        """
        if preparation_display.display_type != 'waiter' and preparation_display.config_category_ids:
            pos_config_id = self.pos_config_id.id if self.pos_config_id else False
            preparation_display = preparation_display.with_context(
                advance_pos_config_id=pos_config_id
            )

        return super()._export_for_ui(preparation_display)

    # =====================================================================
    # OVERRIDE: _send_orders_to_preparation_display
    # =====================================================================
    @api.model
    def _send_orders_to_preparation_display(self, preparation_display_id):
        """Override: waiter solo muestra órdenes propagadas desde cocina."""
        preparation_display = self.env['pos_preparation_display.display'].browse(
            preparation_display_id
        )

        if preparation_display.display_type == 'waiter':
            return self._get_waiter_display_orders(preparation_display)

        return super()._send_orders_to_preparation_display(preparation_display_id)

    def _get_waiter_display_orders(self, preparation_display):
        """Obtiene órdenes para pantalla waiter."""
        order_stages = self.env['pos_preparation_display.order.stage'].search([
            ('preparation_display_id', '=', preparation_display.id),
        ])
        order_ids = list(set(order_stages.mapped('order_id').ids))

        if not order_ids:
            return []

        orders = self.env['pos_preparation_display.order'].browse(order_ids)

        preparation_display_orders = []
        for order in orders:
            order_ui = order._export_for_ui(preparation_display)
            if order_ui:
                preparation_display_orders.append(order_ui)

        return preparation_display_orders
