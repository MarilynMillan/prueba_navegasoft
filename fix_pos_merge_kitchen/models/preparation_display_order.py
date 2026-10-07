from odoo import models, api


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    @api.model
    def reassign_preparation_orders(self, source_order_id, dest_order_id):
        """
        MERGE: Reasigna las órdenes de preparación de una orden POS
        origen a una orden POS destino.
        """
        pdis_orders = self.search([
            ('pos_order_id', '=', source_order_id),
        ])

        if pdis_orders:
            pdis_orders.write({'pos_order_id': dest_order_id})
            self._notify_displays(dest_order_id)

        return True

    @api.model
    def create_split_preparation_order(self, new_order_id, original_order_id, split_lines):
        """
        SPLIT: Crea una pos_preparation_display.order para la orden
        dividida con las líneas que ya fueron enviadas a cocina.
        
        - La nueva pdis_order se crea con displayed=False para que
          NO aparezca como nueva en la pantalla de cocina.
        - La orden original NO se toca — las cantidades en cocina
          se mantienen intactas.
        - NO se notifica a las pantallas de cocina.
        
        Así cuando el mesero comande algo nuevo en la orden dividida,
        _process_preparation_changes encontrará las pdis_lines y
        no las tratará como nuevas.
        """
        if not split_lines:
            return True

        new_order = self.env['pos.order'].browse(new_order_id)
        if not new_order.exists():
            return False

        # Crear la pdis_order para la orden dividida
        # displayed=False para que NO aparezca en cocina como nueva orden
        pdis_order = self.create({
            'displayed': False,
            'pos_order_id': new_order_id,
        })

        for line_data in split_lines:
            product_id = line_data['product_id']
            qty = line_data['qty']
            note = line_data.get('note', '')
            uuid = line_data.get('uuid', '')
            attribute_value_ids = line_data.get('attribute_value_ids', [])

            # Crear pdis_orderline para la orden dividida
            # todo=False para que no aparezca como pendiente
            self.env['pos_preparation_display.orderline'].create({
                'todo': False,
                'internal_note': note,
                'attribute_value_ids': [(6, 0, attribute_value_ids)] if attribute_value_ids else [],
                'product_id': product_id,
                'product_quantity': qty,
                'preparation_display_order_id': pdis_order.id,
                'pos_order_line_uuid': uuid,
            })

        # NO notificamos a las pantallas — el cambio es silencioso
        # La pantalla se actualizará naturalmente cuando el mesero
        # comande algo nuevo o cuando haga cualquier otra acción
        return True

    def _notify_displays(self, order_id):
        """Notifica a las pantallas de preparación para que recarguen."""
        order = self.env['pos.order'].browse(order_id)
        if order.exists():
            displays = self.env['pos_preparation_display.display'].search([
                '|',
                ('pos_config_ids', '=', False),
                ('pos_config_ids', 'in', [order.config_id.id]),
            ])
            for display in displays:
                display._send_load_orders_message()
