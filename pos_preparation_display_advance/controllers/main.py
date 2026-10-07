from odoo import http
from odoo.http import request
from odoo.addons.pos_preparation_display.controllers.main import PosPreparationDisplayController


class PosPreparationDisplayControllerAdvance(PosPreparationDisplayController):

    @http.route(['/pos_preparation_display/web/'], type='http', auth='user', methods=['GET'])
    def display_preparation_web(self, display_id=False):
        preparation_display = request.env['pos_preparation_display.display'].search(
            [('id', '=', int(display_id))]
        )
        if not preparation_display:
            return request.redirect('/odoo/action-pos_preparation_display.action_preparation_display')

        session_info = request.env['ir.http'].session_info()
        session_info['preparation_display'] = preparation_display.read(
            ["id", "name", "access_token"]
        )[0]

        # Inyectar owned_category_ids para que el frontend sepa qué categorías
        # son propias de esta pantalla
        session_info['preparation_display']['owned_category_ids'] = \
            preparation_display.owned_category_ids.ids

        context = {
            'session_info': session_info,
        }
        response = request.render('pos_preparation_display.index', context)
        return response
