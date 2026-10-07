from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosPreparationDisplayConfigCategory(models.Model):
    _name = 'pos_preparation_display.config.category'
    _description = 'Categorías por Punto de Venta en Pantalla de Preparación'

    display_id = fields.Many2one(
        'pos_preparation_display.display',
        string='Pantalla de Preparación',
        required=True,
        ondelete='cascade',
    )
    pos_config_id = fields.Many2one(
        'pos.config',
        string='Punto de Venta',
        required=True,
    )
    category_ids = fields.Many2many(
        'pos.category',
        'preparation_config_category_rel',
        'config_category_id',
        'category_id',
        string='Categorías de Producto',
        required=True,
    )

    _sql_constraints = [
        (
            'unique_display_config',
            'UNIQUE(display_id, pos_config_id)',
            'Ya existe una configuración de categorías para este punto de venta en esta pantalla.'
        ),
    ]

    @api.constrains('category_ids')
    def _check_category_ids(self):
        for record in self:
            if not record.category_ids:
                raise ValidationError(
                    _("Debe asignar al menos una categoría para el punto de venta '%s'.")
                    % record.pos_config_id.name
                )
