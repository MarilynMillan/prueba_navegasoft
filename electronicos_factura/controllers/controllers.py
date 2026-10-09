# -*- coding: utf-8 -*-
from odoo import http

# class ElectronicosFactura(http.Controller):
#     @http.route('/electronicos_factura/electronicos_factura/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/electronicos_factura/electronicos_factura/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('electronicos_factura.listing', {
#             'root': '/electronicos_factura/electronicos_factura',
#             'objects': http.request.env['electronicos_factura.electronicos_factura'].search([]),
#         })

#     @http.route('/electronicos_factura/electronicos_factura/objects/<model("electronicos_factura.electronicos_factura"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('electronicos_factura.object', {
#             'object': obj
#         })