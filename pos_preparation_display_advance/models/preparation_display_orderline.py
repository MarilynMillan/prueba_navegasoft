import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class PosPreparationDisplayOrderline(models.Model):
    _inherit = 'pos_preparation_display.orderline'

    def send_stricked_line_to_next_stage(self, preparation_display_id):
        """Override COMPLETO (sin super) para controlar el timing de notificaciones.

        Problema con super():
        1. super() crea new_order con stage solo para la pantalla actual
        2. super() notifica a TODAS las pantallas que matcheen categorías
        3. COCINA recarga ANTES de que creemos stages → ve new_order como stageless
        4. _get_stageless_orders_in_display le asigna POR PREPARAR → aparece como nueva

        Solución:
        1. Replicamos la lógica nativa
        2. Creamos stages para TODAS las pantallas ANTES de notificar
        3. Para pantallas con owned_category_ids donde las líneas NO pertenecen,
           asignamos última etapa con done=True (invisible)
        4. Notificamos DESPUÉS de que todos los stages existen
        """
        order = self.preparation_display_order_id
        preparation_display = self.env['pos_preparation_display.display'].browse(
            preparation_display_id
        )

        # =====================================================================
        # PASO 1: Guardar stages originales en OTRAS pantallas (antes de todo)
        # =====================================================================
        original_stages_by_display = {}
        for order_stage in order.order_stage_ids:
            display_id = order_stage.preparation_display_id.id
            if display_id != preparation_display_id:
                if display_id not in original_stages_by_display:
                    original_stages_by_display[display_id] = order_stage
                elif order_stage.write_date > original_stages_by_display[display_id].write_date:
                    original_stages_by_display[display_id] = order_stage

        # =====================================================================
        # PASO 2: Lógica nativa — calcular siguiente etapa
        # =====================================================================
        stage_ids = preparation_display.stage_ids
        current_stage_id = order.order_stage_ids.filtered(
            lambda x: x.stage_id in stage_ids
        )
        if not current_stage_id:
            return False

        current_stage_id = current_stage_id[-1]
        current_stage_index = stage_ids.ids.index(current_stage_id.stage_id.id)

        # Protección contra IndexError (bug nativo de doble click)
        if current_stage_index + 1 >= len(stage_ids.ids):
            return False

        next_stage_id = stage_ids.ids[current_stage_index + 1]

        # =====================================================================
        # PASO 3: Crear nueva orden (lógica nativa)
        # =====================================================================
        new_order = self.env['pos_preparation_display.order'].create({
            'displayed': True,
            'pos_order_id': order.pos_order_id.id,
            'pos_config_id': order.pos_config_id.id,
        })

        # Stage para la pantalla actual (lógica nativa)
        new_order.order_stage_ids.create({
            'preparation_display_id': preparation_display_id,
            'stage_id': next_stage_id,
            'order_id': new_order.id,
            'done': False,
        })

        # =====================================================================
        # PASO 4: Mover líneas subrayadas a la nueva orden (lógica nativa)
        # =====================================================================
        category_ids = set()
        for record in self:
            record.todo = True
            record.preparation_display_order_id = new_order.id
            category_ids.update(record.product_id.pos_categ_ids.ids)

        # =====================================================================
        # PASO 5: Crear stages para las OTRAS pantallas ANTES de notificar
        # =====================================================================
        moved_cat_ids = category_ids  # ya tenemos las categorías de las líneas movidas

        stages_to_create = []
        for display_id, original_stage in original_stages_by_display.items():
            other_display = self.env['pos_preparation_display.display'].browse(display_id)

            # Excluir pantallas waiter — se manejan por separado
            if other_display.display_type == 'waiter':
                continue

            if other_display.owned_category_ids:
                owned_cats = set(other_display.owned_category_ids.ids)
                lines_belong_to_other = bool(moved_cat_ids & owned_cats)

                if not lines_belong_to_other:
                    # Las líneas NO son de esta pantalla →
                    # Última etapa + done=True → INVISIBLE
                    last_stage = other_display.stage_ids[-1] if other_display.stage_ids else False
                    if last_stage:
                        stages_to_create.append({
                            'preparation_display_id': display_id,
                            'stage_id': last_stage.id,
                            'order_id': new_order.id,
                            'done': True,
                        })
                        _logger.info(
                            'advance: Lines NOT owned by %s → hiding new_order %s',
                            other_display.name, new_order.id
                        )
                else:
                    # Las líneas SÍ son de esta pantalla → heredar stage original
                    stages_to_create.append({
                        'preparation_display_id': display_id,
                        'stage_id': original_stage.stage_id.id,
                        'order_id': new_order.id,
                        'done': original_stage.done,
                    })
            else:
                # Sin owned categories → heredar stage tal cual
                stages_to_create.append({
                    'preparation_display_id': display_id,
                    'stage_id': original_stage.stage_id.id,
                    'order_id': new_order.id,
                    'done': original_stage.done,
                })

        if stages_to_create:
            self.env['pos_preparation_display.order.stage'].create(stages_to_create)
            _logger.info(
                'advance: Created %d stages for new_order %d BEFORE notify',
                len(stages_to_create), new_order.id
            )

        # =====================================================================
        # PASO 6: AHORA notificar a las pantallas (DESPUÉS de crear stages)
        # =====================================================================
        preparation_displays = self.env['pos_preparation_display.display'].search([
            '&',
            '|', ('pos_config_ids', '=', False),
            ('pos_config_ids', 'in', [order.pos_config_id.id]),
            '|', ('category_ids', 'in', list(category_ids)),
            ('category_ids', '=', False),
        ])

        # Excluir waiter de la notificación de reload
        preparation_displays = preparation_displays.filtered(
            lambda d: d.display_type != 'waiter'
        )

        for p_dis in preparation_displays:
            p_dis._send_load_orders_message()

        # =====================================================================
        # PASO 7: Propagación a WAITER (si llegó a última etapa de kitchen)
        # =====================================================================
        try:
            if preparation_display.display_type != 'kitchen':
                return new_order.id

            if not preparation_display.stage_ids:
                return new_order.id

            last_stage_id = preparation_display.stage_ids[-1].id
            if next_stage_id != last_stage_id:
                return new_order.id

            waiter_displays = self.env['pos_preparation_display.display'].search([
                ('display_type', '=', 'waiter'),
                ('source_category_ids.source_display_id', '=', preparation_display.id),
            ])

            if not waiter_displays:
                return new_order.id

            pos_config_id = (
                new_order.pos_order_id.config_id.id
                if new_order.pos_order_id else False
            )
            if pos_config_id:
                waiter_displays = waiter_displays.filtered(
                    lambda d: not d.pos_config_ids
                    or pos_config_id in d.pos_config_ids.ids
                )

            for waiter_display in waiter_displays:
                try:
                    new_order._propagate_to_waiter(waiter_display, preparation_display)
                except Exception as e:
                    _logger.error(
                        "Error propagando orden parcial %s a waiter %s: %s",
                        new_order.id, waiter_display.id, str(e)
                    )

        except Exception as e:
            _logger.error(
                "Error en send_stricked_line waiter hook: %s",
                str(e)
            )

        return new_order.id
