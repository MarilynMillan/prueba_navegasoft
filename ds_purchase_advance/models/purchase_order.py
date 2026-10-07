# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


# =============================================================================
# PURCHASE ORDER
# =============================================================================
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # --- Requisiciones ---
    ds_requisition_ids = fields.Many2many(
        'ds.purchase.requisition',
        'ds_po_requisition_rel',
        'purchase_order_id',
        'requisition_id',
        string='Requisiciones',
        help='Requisiciones de compra vinculadas a esta orden.',
        copy=False,
    )
    ds_requisition_count = fields.Integer(
        string='# Requisiciones',
        compute='_compute_ds_requisition_count',
    )

    @api.depends('ds_requisition_ids')
    def _compute_ds_requisition_count(self):
        for order in self:
            order.ds_requisition_count = len(order.ds_requisition_ids)

    # -----------------------------------------------------------------
    # Supplierinfo update: al confirmar la OC, actualizar precios
    # -----------------------------------------------------------------
    def write(self, vals):
        # Capturar las OC que NO estaban confirmadas antes del write
        not_confirmed = self.filtered(
            lambda r: r.state not in ('purchase', 'done')
        )
        res = super().write(vals)
        # Si el estado cambió a confirmado, actualizar precios
        if vals.get('state', '') in ('purchase', 'done'):
            not_confirmed.mapped(
                'order_line'
            )._ds_update_supplierinfo_price()
        return res

    # -----------------------------------------------------------------
    # Acciones de requisiciones
    # -----------------------------------------------------------------
    def action_view_requisitions(self):
        self.ensure_one()
        requisitions = self.ds_requisition_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Requisiciones'),
            'res_model': 'ds.purchase.requisition',
            'view_mode': 'list,form',
            'domain': [('id', 'in', requisitions.ids)],
            'context': self.env.context,
        }
        if len(requisitions) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = requisitions.id
        return action

    def action_load_from_requisitions(self):
        self.ensure_one()
        if not self.ds_requisition_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Requisiciones'),
                    'message': _(
                        'Primero selecciona al menos una requisición '
                        'en el campo "Requisiciones".'
                    ),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        wizard = self.env['ds.requisition.load.wizard'].create({
            'purchase_order_id': self.id,
            'requisition_ids': [(6, 0, self.ds_requisition_ids.ids)],
        })
        wizard._load_pending_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cargar Productos de Requisiciones'),
            'res_model': 'ds.requisition.load.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context,
        }


# =============================================================================
# PURCHASE ORDER LINE
# =============================================================================
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # --- Campos de trazabilidad de requisiciones ---
    ds_requisition_line_id = fields.Many2one(
        'ds.purchase.requisition.line',
        string='Línea de Requisición',
        copy=False,
        index=True,
        help='Línea de requisición que originó esta línea de OC.',
    )
    ds_requisition_id = fields.Many2one(
        related='ds_requisition_line_id.requisition_id',
        string='Requisición',
        store=True,
        readonly=True,
    )
    ds_qty_requisition_original = fields.Float(
        string='Cant. Solicitada (Req.)',
        digits='Product Unit of Measure',
        readonly=True,
        help='Cantidad original solicitada en la requisición.',
    )
    ds_qty_difference = fields.Float(
        string='Diferencia vs Req.',
        compute='_compute_qty_difference',
        digits='Product Unit of Measure',
        help='Positivo = se pidió más, Negativo = se pidió menos.',
    )

    @api.depends('product_qty', 'ds_qty_requisition_original')
    def _compute_qty_difference(self):
        for line in self:
            if line.ds_requisition_line_id:
                line.ds_qty_difference = (
                    line.product_qty - line.ds_qty_requisition_original
                )
            else:
                line.ds_qty_difference = 0.0

    # -----------------------------------------------------------------
    # CRUD overrides para requisiciones + supplierinfo
    # -----------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Actualizar estados de requisiciones vinculadas
        lines._update_requisition_states()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'product_qty' in vals:
            self._update_requisition_states()
        if 'price_unit' in vals:
            self._ds_update_supplierinfo_price()
        return res

    def unlink(self):
        requisitions = self.mapped(
            'ds_requisition_line_id.requisition_id'
        )
        res = super().unlink()
        requisitions._update_state()
        return res

    def _update_requisition_states(self):
        requisitions = self.mapped(
            'ds_requisition_line_id.requisition_id'
        )
        requisitions._update_state()

    # -----------------------------------------------------------------
    # Actualización automática de supplierinfo
    # -----------------------------------------------------------------
    def _ds_update_supplierinfo_price(self):
        """Actualiza el precio en product.supplierinfo al confirmar
        la OC. Sin búsquedas históricas: la OC que se confirma
        siempre tiene el precio más actual.
        """
        for line in self.filtered(
            lambda r: (
                not r.display_type
                and r.order_id.state in ('purchase', 'done')
            )
        ):
            # Buscar el supplierinfo correspondiente
            params = {'order_id': line.order_id}
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=(
                    line.order_id.date_order
                    and line.order_id.date_order.date()
                ),
                uom_id=line.product_uom,
                params=params,
            )
            if seller:
                line._ds_write_supplierinfo(seller)

    def _ds_write_supplierinfo(self, seller):
        """Escribe el nuevo precio en el supplierinfo.
        Maneja conversión de moneda y UdM.
        """
        self.ensure_one()
        new_price = self.price_unit

        # Convertir moneda si es diferente
        if self.currency_id and self.currency_id != seller.currency_id:
            new_price = self.currency_id._convert(
                new_price,
                seller.currency_id,
                seller.company_id,
                self.date_order or fields.Date.today(),
            )

        # Convertir UdM si es diferente
        if self.product_uom and self.product_uom != seller.product_uom:
            new_price = self.product_uom._compute_price(
                new_price, seller.product_uom
            )

        # Actualizar precio si cambió
        if new_price != seller.price:
            seller.sudo().price = new_price

        # Actualizar descuento si cambió (y si el campo existe)
        if hasattr(seller, 'discount'):
            if self.discount != seller.discount:
                seller.sudo().discount = self.discount
