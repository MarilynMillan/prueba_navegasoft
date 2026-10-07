# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DSRequisitionLoadWizard(models.TransientModel):
    _name = 'ds.requisition.load.wizard'
    _description = 'Cargar Productos desde Requisiciones'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Orden de Compra',
        required=True,
        readonly=True,
    )
    requisition_ids = fields.Many2many(
        'ds.purchase.requisition',
        string='Requisiciones',
        readonly=True,
    )
    line_ids = fields.One2many(
        'ds.requisition.load.wizard.line',
        'wizard_id',
        string='Líneas Disponibles',
    )

    def _load_pending_lines(self):
        self.ensure_one()
        self.line_ids.unlink()

        lines_vals = []
        for requisition in self.requisition_ids:
            for req_line in requisition.line_ids:
                if req_line.qty_pending <= 0:
                    continue
                lines_vals.append({
                    'wizard_id': self.id,
                    'requisition_line_id': req_line.id,
                    'requisition_id': requisition.id,
                    'product_id': req_line.product_id.id,
                    'product_uom_id': req_line.product_uom_id.id,
                    'qty_requested': req_line.qty_requested,
                    'qty_already_ordered': req_line.qty_ordered,
                    'qty_pending': req_line.qty_pending,
                    'qty_to_order': req_line.qty_pending,
                    'selected': False,
                })

        if not lines_vals:
            raise UserError(
                _('No hay productos pendientes en las requisiciones '
                  'seleccionadas. Todas las líneas ya fueron asignadas '
                  'a órdenes de compra.')
            )

        self.env['ds.requisition.load.wizard.line'].create(lines_vals)

    def action_select_all(self):
        self.line_ids.write({'selected': True})
        return self._reopen()

    def action_deselect_all(self):
        self.line_ids.write({'selected': False})
        return self._reopen()

    def action_confirm(self):
        self.ensure_one()
        selected = self.line_ids.filtered('selected')
        if not selected:
            raise UserError(_('No has seleccionado ningún producto.'))

        po = self.purchase_order_id
        PurchaseOrderLine = self.env['purchase.order.line']

        for wiz_line in selected:
            if wiz_line.qty_to_order <= 0:
                continue

            if wiz_line.qty_to_order > wiz_line.qty_pending:
                raise UserError(
                    _('La cantidad a pedir para "%s" (%s) excede '
                      'la cantidad pendiente (%s).')
                    % (
                        wiz_line.product_id.display_name,
                        wiz_line.qty_to_order,
                        wiz_line.qty_pending,
                    )
                )

            existing = PurchaseOrderLine.search([
                ('order_id', '=', po.id),
                ('ds_requisition_line_id', '=',
                 wiz_line.requisition_line_id.id),
            ], limit=1)

            if existing:
                existing.product_qty += wiz_line.qty_to_order
            else:
                line_vals = {
                    'order_id': po.id,
                    'product_id': wiz_line.product_id.id,
                    'product_qty': wiz_line.qty_to_order,
                    'product_uom': wiz_line.product_uom_id.id,
                    'ds_requisition_line_id': (
                        wiz_line.requisition_line_id.id
                    ),
                    'ds_qty_requisition_original': (
                        wiz_line.qty_requested
                    ),
                }
                new_line = PurchaseOrderLine.new(line_vals)
                new_line.onchange_product_id()
                new_line.product_qty = wiz_line.qty_to_order
                create_vals = new_line._convert_to_write(new_line._cache)
                create_vals.update({
                    'ds_requisition_line_id': (
                        wiz_line.requisition_line_id.id
                    ),
                    'ds_qty_requisition_original': (
                        wiz_line.qty_requested
                    ),
                })
                PurchaseOrderLine.create(create_vals)

        reqs = selected.mapped('requisition_id')
        po.ds_requisition_ids = [(4, req.id) for req in reqs]

        return {'type': 'ir.actions.act_window_close'}

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class DSRequisitionLoadWizardLine(models.TransientModel):
    _name = 'ds.requisition.load.wizard.line'
    _description = 'Línea del Wizard de Carga de Requisiciones'
    _order = 'requisition_id, product_id'

    wizard_id = fields.Many2one(
        'ds.requisition.load.wizard',
        required=True,
        ondelete='cascade',
    )
    selected = fields.Boolean(string='Sel.', default=False)

    requisition_line_id = fields.Many2one(
        'ds.purchase.requisition.line',
        string='Línea Requisición',
        required=True,
    )
    requisition_id = fields.Many2one(
        'ds.purchase.requisition',
        string='Requisición',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UdM',
        readonly=True,
    )
    qty_requested = fields.Float(
        string='Cant. Solicitada',
        digits='Product Unit of Measure',
        readonly=True,
    )
    qty_already_ordered = fields.Float(
        string='Ya en OC',
        digits='Product Unit of Measure',
        readonly=True,
    )
    qty_pending = fields.Float(
        string='Pendiente',
        digits='Product Unit of Measure',
        readonly=True,
    )
    qty_to_order = fields.Float(
        string='Cant. a Pedir',
        digits='Product Unit of Measure',
        help='Cantidad que se agregará a la Orden de Compra.',
    )
