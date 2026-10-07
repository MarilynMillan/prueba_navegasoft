# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DSPurchaseRequisition(models.Model):
    _name = 'ds.purchase.requisition'
    _description = 'Requisición de Compra por Sede'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('in_progress', 'En Proceso'),
        ('done', 'Completada'),
        ('cancel', 'Cancelada'),
    ], string='Estado', default='draft', tracking=True, copy=False)

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Sede',
        required=True,
        tracking=True,
        default=lambda self: self._default_warehouse(),
    )
    user_id = fields.Many2one(
        'res.users',
        string='Solicitante',
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,
    )
    date_request = fields.Datetime(
        string='Fecha de Solicitud',
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )
    date_deadline = fields.Date(
        string='Fecha Límite',
        tracking=True,
        help='Fecha máxima en la que se necesitan los productos.',
    )
    notes = fields.Html(string='Notas')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )

    # --- Líneas ---
    line_ids = fields.One2many(
        'ds.purchase.requisition.line',
        'requisition_id',
        string='Líneas de Requisición',
        copy=True,
    )

    # --- Campos calculados ---
    line_count = fields.Integer(
        string='# Líneas',
        compute='_compute_line_count',
    )
    progress = fields.Float(
        string='Progreso',
        compute='_compute_progress',
        store=True,
        help='Porcentaje de productos asignados a órdenes de compra.',
    )
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Órdenes de Compra',
        compute='_compute_purchase_orders',
    )
    purchase_order_count = fields.Integer(
        string='# OC',
        compute='_compute_purchase_orders',
    )

    # -------------------------------------------------------------------------
    # Defaults
    # -------------------------------------------------------------------------
    def _default_warehouse(self):
        return self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.qty_ordered', 'line_ids.qty_requested')
    def _compute_progress(self):
        for rec in self:
            total_requested = sum(rec.line_ids.mapped('qty_requested'))
            total_ordered = sum(rec.line_ids.mapped('qty_ordered'))
            if total_requested > 0:
                rec.progress = min(
                    (total_ordered / total_requested) * 100, 100.0
                )
            else:
                rec.progress = 0.0

    def _compute_purchase_orders(self):
        for rec in self:
            po_lines = self.env['purchase.order.line'].search([
                ('ds_requisition_line_id', 'in', rec.line_ids.ids),
            ])
            orders = po_lines.mapped('order_id')
            rec.purchase_order_ids = orders
            rec.purchase_order_count = len(orders)

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'ds.purchase.requisition'
                ) or _('Nuevo')
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(
                    _('Solo se pueden eliminar requisiciones en estado '
                      'Borrador o Cancelada.')
                )
        return super().unlink()

    # -------------------------------------------------------------------------
    # Acciones de estado
    # -------------------------------------------------------------------------
    def action_send(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(
                    _('No puedes enviar una requisición sin líneas.')
                )
            rec.state = 'sent'

    def action_cancel(self):
        for rec in self:
            has_ordered = any(
                line.qty_ordered > 0 for line in rec.line_ids
            )
            if has_ordered:
                raise UserError(
                    _('No se puede cancelar la requisición "%s" porque '
                      'tiene productos ya asignados a órdenes de compra. '
                      'Cancela primero las OC relacionadas.') % rec.name
                )
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(
                    _('Solo se puede pasar a borrador desde Cancelada.')
                )
            rec.state = 'draft'

    def _update_state(self):
        for rec in self:
            if rec.state in ('draft', 'cancel'):
                continue
            all_done = all(
                line.qty_pending <= 0 for line in rec.line_ids
            )
            any_ordered = any(
                line.qty_ordered > 0 for line in rec.line_ids
            )
            if all_done:
                rec.state = 'done'
            elif any_ordered:
                rec.state = 'in_progress'
            else:
                rec.state = 'sent'

    # -------------------------------------------------------------------------
    # Smart buttons
    # -------------------------------------------------------------------------
    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'purchase.purchase_form_action'
        )
        orders = self.purchase_order_ids
        if len(orders) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = orders.id
        else:
            action['domain'] = [('id', 'in', orders.ids)]
        return action


class DSPurchaseRequisitionLine(models.Model):
    _name = 'ds.purchase.requisition.line'
    _description = 'Línea de Requisición de Compra'
    _order = 'sequence, id'

    requisition_id = fields.Many2one(
        'ds.purchase.requisition',
        string='Requisición',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Secuencia', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        domain=[('purchase_ok', '=', True)],
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UdM',
        related='product_id.uom_id',
        readonly=True,
        store=True,
    )
    qty_requested = fields.Float(
        string='Cantidad Solicitada',
        required=True,
        digits='Product Unit of Measure',
    )
    qty_ordered = fields.Float(
        string='Cantidad en OC',
        compute='_compute_qty_ordered',
        store=True,
        digits='Product Unit of Measure',
        help='Cantidad total ya incluida en Órdenes de Compra.',
    )
    qty_pending = fields.Float(
        string='Cantidad Pendiente',
        compute='_compute_qty_ordered',
        store=True,
        digits='Product Unit of Measure',
        help='Cantidad que aún no ha sido asignada a ninguna OC.',
    )
    line_state = fields.Selection([
        ('pending', 'Pendiente'),
        ('partial', 'Parcial'),
        ('done', 'Completa'),
    ], string='Estado Línea', compute='_compute_qty_ordered', store=True)

    purchase_line_ids = fields.One2many(
        'purchase.order.line',
        'ds_requisition_line_id',
        string='Líneas de OC',
    )

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('qty_requested')
    def _check_qty_requested(self):
        for line in self:
            if line.qty_requested <= 0:
                raise ValidationError(
                    _('La cantidad solicitada debe ser mayor a 0 '
                      'para "%s".') % line.product_id.display_name
                )

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @api.depends('purchase_line_ids.product_qty',
                 'purchase_line_ids.order_id.state',
                 'qty_requested')
    def _compute_qty_ordered(self):
        for line in self:
            valid_po_lines = line.purchase_line_ids.filtered(
                lambda pol: pol.order_id.state != 'cancel'
            )
            ordered = sum(valid_po_lines.mapped('product_qty'))
            line.qty_ordered = ordered
            line.qty_pending = max(line.qty_requested - ordered, 0.0)

            if ordered <= 0:
                line.line_state = 'pending'
            elif line.qty_pending > 0:
                line.line_state = 'partial'
            else:
                line.line_state = 'done'
