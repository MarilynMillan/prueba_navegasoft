# -*- coding: utf-8 -*-
from odoo import http

# class BaseElectronicos(http.Controller):
#     @http.route('/base_electronicos/base_electronicos/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/base_electronicos/base_electronicos/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('base_electronicos.listing', {
#             'root': '/base_electronicos/base_electronicos',
#             'objects': http.request.env['base_electronicos.base_electronicos'].search([]),
#         })

#     @http.route('/base_electronicos/base_electronicos/objects/<model("base_electronicos.base_electronicos"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('base_electronicos.object', {
#             'object': obj
#         })