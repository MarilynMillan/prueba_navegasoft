# -*- coding: utf-8 -*-
from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def log_waiter_change(self, order_uuid, previous_waiter, new_waiter, changed_by):
        """
        Registra el cambio de mesero en el chatter de la orden POS.

        Se llama vía RPC desde el frontend (fire-and-forget).
        Busca la orden por UUID que es el identificador más confiable
        disponible en el POS antes de que la orden se cierre.

        :param order_uuid: UUID de la orden POS
        :param previous_waiter: Nombre del mesero anterior
        :param new_waiter: Nombre del nuevo mesero
        :param changed_by: Nombre del manager que autorizó
        :return: True/False
        """
        try:
            order = self.search([('uuid', '=', order_uuid)], limit=1)

            if not order:
                _logger.info(
                    "pos_change_waiter: Orden UUID '%s' aún no sincronizada. "
                    "El cambio de mesero se aplicó en el POS.", order_uuid
                )
                return False

            body = (
                "🔄 Cambio de Mesero\n"
                "Mesero anterior: %s\n"
                "Nuevo mesero: %s\n"
                "Autorizado por: %s"
            ) % (
                previous_waiter or '(sin asignar)',
                new_waiter,
                changed_by,
            )

            order.message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return True

        except Exception:
            _logger.exception(
                "pos_change_waiter: Error registrando cambio en orden UUID '%s'",
                order_uuid,
            )
            return False
