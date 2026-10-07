# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models

STATES = [
    ('orderline_qty_update','Quantity Update'),
    ('orderline_deleted','Orderline Deleted'),
    ('order_deleted','Order Deleted'),
    ('session_close','Session Close')
]

class ManagerApproval(models.Model):
    _name = "manager.approval"
    _description = "Manager Approval in restaurants"
    _order = 'id desc'

    session_id = fields.Many2one('pos.session', string='Session', required=True, index=True, domain="[('state', '=', 'opened')]")
    receipt_number = fields.Char(string='Receipt Number')
    manager_approved = fields.Many2one('hr.employee', string='Manager Approved', readonly=True)
    cashier = fields.Many2one('hr.employee', string='Cashier', readonly=True)
    state = fields.Selection(STATES, string="Action")
    order_number = fields.Char(string='Order Number')

    @api.model
    def getting_all_data(self,kwargs):
        if(kwargs.get('state') == 'session_close'):
            new = 'session_close'
        elif(kwargs.get('state') == 'orderline_qty_update'):
            new = 'orderline_qty_update'
        elif(kwargs.get('state') == 'order_deleted'):
            new = 'order_deleted'
        else:
            new = 'orderline_deleted'
        self.env['manager.approval'].create({
            'session_id': kwargs.get('session_id'),
            'cashier': kwargs.get('cashier1'),
            'manager_approved': kwargs.get('manager'),
            'state': new,
            'receipt_number': kwargs.get('receipt'),
            'order_number': kwargs.get('order_num')
        })
