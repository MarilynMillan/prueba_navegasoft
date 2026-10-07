from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosPreparationDisplaySourceCategory(models.Model):
    _name = 'pos_preparation_display.source.category'
    _description = 'Categorías por Pantalla Fuente en Pantalla de Meseros'

    display_id = fields.Many2one(
        'pos_preparation_display.display',
        string='Pantalla de Meseros',
        required=True,
        ondelete='cascade',
    )
    source_display_id = fields.Many2one(
        'pos_preparation_display.display',
        string='Pantalla Fuente',
        required=True,
        domain="[('display_type', '=', 'kitchen')]",
    )
    category_ids = fields.Many2many(
        'pos.category',
        'preparation_source_category_rel',
        'source_category_id',
        'category_id',
        string='Categorías de Producto',
        required=True,
    )

    _sql_constraints = [
        (
            'unique_display_source',
            'UNIQUE(display_id, source_display_id)',
            'Ya existe una configuración para esta pantalla fuente.'
        ),
    ]

    @api.constrains('category_ids')
    def _check_category_ids(self):
        for record in self:
            if not record.category_ids:
                raise ValidationError(
                    _("Debe asignar al menos una categoría para la pantalla fuente '%s'.")
                    % record.source_display_id.name
                )
