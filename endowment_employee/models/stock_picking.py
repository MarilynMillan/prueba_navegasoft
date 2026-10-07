from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        help="Empleado al que se le asigna la dotación."
    )

    has_dotacion_product = fields.Boolean(
        string="Tiene Dotación",
        compute='_compute_has_dotacion_product', 
        store=True, 
        depends=['move_ids.product_id.categ_id.is_dotacion'] 
    )

    @api.depends('move_ids.product_id.categ_id.is_dotacion')
    def _compute_has_dotacion_product(self):
        for picking in self:
            is_dotacion = any(
                move.product_id.categ_id.is_dotacion
                for move in picking.move_ids_without_package
            )
            picking.has_dotacion_product = is_dotacion

    @api.model
    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if picking.has_dotacion_product and not picking.employee_id:
                raise UserError("Debe seleccionar un empleado para órdenes con productos de dotación.")
                
            if picking.employee_id:
                total_cost = 0.0
                dotacion_lines = []
                for move in picking.move_ids_without_package:
                    product = move.product_id
                    if product.categ_id.is_dotacion:  # boolean en categoría
                        line_cost = product.standard_price * move.product_uom_qty
                        total_cost += line_cost
                        dotacion_lines.append((product.display_name, line_cost))

                if total_cost > 0:
                    self.env["hr.employee.dotacion"].create({
                        "employee_id": picking.employee_id.id,
                        "picking_id": picking.id,
                        "cost": total_cost,
                        "date": picking.scheduled_date or fields.Date.today(),
                    })
        return res