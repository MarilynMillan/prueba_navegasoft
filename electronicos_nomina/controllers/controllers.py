# from odoo import http

# class ElectronicosNomina(http.Controller):
#     @http.route('/electronicos_nomina/electronicos_nomina/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/electronicos_nomina/electronicos_nomina/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('electronicos_nomina.listing', {
#             'root': '/electronicos_nomina/electronicos_nomina',
#             'objects': http.request.env['electronicos_nomina.electronicos_nomina'].search([]),
#         })

#     @http.route('/electronicos_nomina/electronicos_nomina/objects/<model("electronicos_nomina.electronicos_nomina"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('electronicos_nomina.object', {
#             'object': obj
#         })