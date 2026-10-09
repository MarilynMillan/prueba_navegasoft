from odoo import http

# class MediosMagneticos(http.Controller):
#     @http.route('/medios_magneticos/medios_magneticos/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/medios_magneticos/medios_magneticos/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('medios_magneticos.listing', {
#             'root': '/medios_magneticos/medios_magneticos',
#             'objects': http.request.env['medios_magneticos.medios_magneticos'].search([]),
#         })

#     @http.route('/medios_magneticos/medios_magneticos/objects/<model("medios_magneticos.medios_magneticos"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('medios_magneticos.object', {
#             'object': obj
#         })