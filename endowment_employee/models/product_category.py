from odoo import fields, models

class ProductCategory(models.Model):
    _inherit = "product.category"

    is_dotacion = fields.Boolean(
        string="Es dotación",
        help="Marcar si esta categoría corresponde a productos de dotación."
    )