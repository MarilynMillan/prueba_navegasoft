# -*- coding: utf-8 -*-
# from odoo import http


# class FixExtructurasDePago(http.Controller):
#     @http.route('/fix_extructuras_de_pago/fix_extructuras_de_pago', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fix_extructuras_de_pago/fix_extructuras_de_pago/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('fix_extructuras_de_pago.listing', {
#             'root': '/fix_extructuras_de_pago/fix_extructuras_de_pago',
#             'objects': http.request.env['fix_extructuras_de_pago.fix_extructuras_de_pago'].search([]),
#         })

#     @http.route('/fix_extructuras_de_pago/fix_extructuras_de_pago/objects/<model("fix_extructuras_de_pago.fix_extructuras_de_pago"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fix_extructuras_de_pago.object', {
#             'object': obj
#         })
