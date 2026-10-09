# -*- coding: utf-8 -*-
from odoo import http

# class ElectronicosPos(http.Controller):
#     @http.route('/electronicos_pos/electronicos_pos/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/electronicos_pos/electronicos_pos/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('electronicos_pos.listing', {
#             'root': '/electronicos_pos/electronicos_pos',
#             'objects': http.request.env['electronicos_pos.electronicos_pos'].search([]),
#         })

#     @http.route('/electronicos_pos/electronicos_pos/objects/<model("electronicos_pos.electronicos_pos"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('electronicos_pos.object', {
#             'object': obj
#         })