from odoo import api, fields, models


class PosPreparationDisplay(models.Model):
    _inherit = 'pos_preparation_display.display'

    # =====================================================================
    # CAMPOS v1: Categorías por POS (para pantallas kitchen)
    # =====================================================================
    config_category_ids = fields.One2many(
        'pos_preparation_display.config.category',
        'display_id',
        string='Categorías por Punto de Venta',
    )

    # =====================================================================
    # CAMPOS v2: Tipo de pantalla + Pantallas fuente (para waiter)
    # =====================================================================
    display_type = fields.Selection(
        [('kitchen', 'Cocina'), ('waiter', 'Mesero')],
        string='Tipo de Pantalla',
        default='kitchen',
        required=True,
    )

    source_category_ids = fields.One2many(
        'pos_preparation_display.source.category',
        'display_id',
        string='Categorías por Pantalla Fuente',
    )

    # =====================================================================
    # CAMPOS v3: Categorías propias (owned) para aislamiento entre pantallas
    # =====================================================================
    owned_category_ids = fields.Many2many(
        'pos.category',
        'preparation_display_owned_category_rel',
        'display_id',
        'category_id',
        string='Categorías Propias',
        help='Categorías que esta pantalla "posee". Los productos de otras '
             'categorías se muestran en color diferente y las interacciones '
             'de subrayado individual no afectan a otras pantallas.',
    )

    # =====================================================================
    # v1: CATEGORÍAS POR POS (pantallas kitchen)
    # =====================================================================
    def _get_pos_category_ids(self, pos_config_id=False):
        """Retorna categorías específicas del POS si existen (v1)."""
        self.ensure_one()

        if pos_config_id and self.config_category_ids:
            config_category = self.config_category_ids.filtered(
                lambda cc: cc.pos_config_id.id == pos_config_id
            )
            if config_category:
                return config_category.category_ids

        # Fallback al comportamiento original
        if not self.category_ids:
            return self.env['pos.category'].search([])
        return self.category_ids

    def _should_include(self, orderline):
        """Override: filtra orderlines según tipo de pantalla.

        - waiter: filtra por categorías de pantallas fuente que ya marcaron "Listo"
        - kitchen: usa categorías por POS via contexto (v1)

        Firma idéntica al nativo para compatibilidad total.
        """
        if self.display_type == 'waiter':
            return self._waiter_should_include(orderline)

        # kitchen: lógica v1 - obtener pos_config_id del contexto
        pos_config_id = self.env.context.get('advance_pos_config_id', False)
        if pos_config_id and self.config_category_ids:
            category_ids = self._get_pos_category_ids(pos_config_id=pos_config_id)
            return any(
                categ_id in category_ids.ids
                for categ_id in orderline.product_id.pos_categ_ids.ids
            )

        # Sin config v1: usar super() nativo
        return super()._should_include(orderline)

    def _waiter_should_include(self, orderline):
        """Para waiter: solo incluir líneas cuya categoría pertenezca a una
        pantalla fuente que ya marcó la orden como 'Listo'.
        """
        order = orderline.preparation_display_order_id
        line_cat_ids = set(orderline.product_id.pos_categ_ids.ids)

        for source_config in self.source_category_ids:
            allowed_cats = set(source_config.category_ids.ids)
            if not (line_cat_ids & allowed_cats):
                continue

            source = source_config.source_display_id
            if not source.stage_ids:
                continue
            last_stage_id = source.stage_ids[-1].id

            for stage in order.order_stage_ids:
                if (stage.preparation_display_id.id == source.id
                        and stage.stage_id.id == last_stage_id):
                    return True

        return False

    # =====================================================================
    # OVERRIDES DE DATOS PARA UI
    # =====================================================================
    def get_preparation_display_data(self):
        """Override: envía categorías según tipo de pantalla + owned_category_ids + display_type."""
        result = super().get_preparation_display_data()

        # Enviar display_type al frontend
        result['display_type'] = self.display_type

        # Enviar owned_category_ids al frontend para distinción visual
        result['owned_category_ids'] = self.owned_category_ids.ids

        if self.display_type == 'kitchen' and self.config_category_ids:
            all_categories = self.env['pos.category']
            for config_cat in self.config_category_ids:
                all_categories |= config_cat.category_ids
            result['categories'] = all_categories.read(['id', 'display_name', 'sequence'])

        elif self.display_type == 'waiter' and self.source_category_ids:
            all_categories = self.env['pos.category']
            for source_cat in self.source_category_ids:
                all_categories |= source_cat.category_ids
            result['categories'] = all_categories.read(['id', 'display_name', 'sequence'])

        return result

    def _compute_order_count(self):
        """Override: separa conteo waiter del kitchen."""
        waiter_displays = self.filtered(lambda d: d.display_type == 'waiter')
        kitchen_displays = self - waiter_displays

        if kitchen_displays:
            super(PosPreparationDisplay, kitchen_displays)._compute_order_count()

        for preparation_display in waiter_displays:
            preparation_display._compute_order_count_waiter()

    def _compute_order_count_waiter(self):
        """Conteo de órdenes para pantallas waiter."""
        progress_order_count = 0

        order_stages = self.env['pos_preparation_display.order.stage'].search([
            ('preparation_display_id', '=', self.id),
            ('create_date', '>=', fields.Date.today()),
        ])

        if self.stage_ids:
            last_stage_id = self.stage_ids[-1].id
            for os in order_stages:
                if os.stage_id.id != last_stage_id:
                    progress_order_count += 1

        self.order_count = progress_order_count

        done_stages = order_stages.filtered(lambda s: s.done)
        completed_order_times = [
            (os.write_date - os.order_id.create_date).total_seconds()
            for os in done_stages
        ]
        self.average_time = (
            round(sum(completed_order_times) / len(completed_order_times) / 60)
            if completed_order_times else 0
        )

    # =====================================================================
    # v2: ETAPAS POR DEFECTO PARA WAITER
    # =====================================================================
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.display_type == 'waiter' and not record.stage_ids:
                self.env['pos_preparation_display.stage'].create([
                    {
                        'name': 'Por Entregar',
                        'preparation_display_id': record.id,
                        'sequence': 1,
                    },
                    {
                        'name': 'Listo',
                        'preparation_display_id': record.id,
                        'sequence': 2,
                    },
                ])
        return records
