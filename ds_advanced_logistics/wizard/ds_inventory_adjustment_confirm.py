# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class DSInventoryAdjustmentConfirm(models.TransientModel):
    """Diálogo de confirmación: motivo y responsables del conteo."""
    _name = 'ds.inventory.adjustment.confirm'
    _description = 'Confirmación de Ajuste Retroactivo'

    adjustment_id = fields.Many2one(
        'ds.inventory.adjustment',
        string='Ajuste',
        required=True,
    )
    reason = fields.Text(
        string='Motivo del Inventario',
        required=True,
    )
    responsible_employee_ids = fields.Many2many(
        'hr.employee',
        'ds_inv_adj_confirm_employee_rel',
        'confirm_id',
        'employee_id',
        string='Responsables del Conteo',
        required=True,
    )

    def action_confirm_and_apply(self):
        """Confirma y aplica el ajuste."""
        self.ensure_one()
        self.adjustment_id.apply_adjustment(
            reason=self.reason,
            employee_ids=self.responsible_employee_ids.ids,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ds.inventory.adjustment',
            'res_id': self.adjustment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
