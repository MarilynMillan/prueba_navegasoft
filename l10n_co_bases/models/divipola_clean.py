# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_unify_divipola_l10n_co_bases(self):
        """
        Botón manual desde el formulario de partner para unificar y depurar
        ciudades creadas por l10n_co_bases.
        Se ejecuta a nivel global, no solo para este partner.
        """
        self.ensure_one()
        env = self.env

        MODULE_NAME = 'l10n_co_bases'
        COUNTRY_CODE = 'CO'

        IrModelData = env['ir.model.data']
        City = env['res.city']
        Partner = env['res.partner']
        Country = env['res.country'].search([('code', '=', COUNTRY_CODE)], limit=1)

        if not Country:
            _logger.warning(
                "DIVIPOLA cleanup: no se encontró país con código %s", COUNTRY_CODE
            )
            return self._notify_divipola(
                "No se encontró el país CO. Revisa la configuración de países.",
                notif_type="warning",
            )

        def field_exists(model, field):
            return field in model._fields

        partner_city_fields = [
            'city_id',
            'l10n_co_edi_city_id',
            'l10n_co_edi_municipality_id',
        ]

        # Solo ciudades creadas por l10n_co_bases (ajusta si quieres rango/patrón)
        imd_domain = [
            ('module', '=', MODULE_NAME),
            ('model', '=', 'res.city'),
        ]
        imds = IrModelData.search(imd_domain)
        cities = City.browse(imds.mapped('res_id')).filtered(
            lambda c: c.country_id.id == Country.id
        )

        _logger.info(
            "DIVIPOLA cleanup: encontradas %s ciudades con xml_id de %s",
            len(cities),
            MODULE_NAME,
        )

        total_deleted = 0
        total_without_canon = 0

        for city in cities:
            # buscar ciudad canónica con mismo code + state + país
            canonical = City.search([
                ('id', '!=', city.id),
                ('code', '=', city.code),
                ('state_id', '=', city.state_id.id),
                ('country_id', '=', city.country_id.id),
            ], limit=1)

            if not canonical:
                total_without_canon += 1
                _logger.info(
                    "DIVIPOLA cleanup: SIN CANÓNICA para %s (id=%s, code=%s, state=%s)",
                    city.display_name,
                    city.id,
                    city.code,
                    city.state_id.display_name,
                )
                continue

            _logger.info(
                "DIVIPOLA cleanup: unificando %s (id=%s) -> %s (id=%s)",
                city.display_name,
                city.id,
                canonical.display_name,
                canonical.id,
            )

            # Reasignar partners
            for fname in partner_city_fields:
                if not field_exists(Partner, fname):
                    continue
                partners = Partner.search([(fname, '=', city.id)])
                if partners:
                    _logger.info(
                        "DIVIPOLA cleanup: reasignando %s partners.%s de city %s a %s",
                        partners.__len__(),
                        fname,
                        city.id,
                        canonical.id,
                    )
                    partners.write({fname: canonical.id})

            # Borrar ciudad + su xml_id
            city_imds = imds.filtered(lambda r: r.res_id == city.id)
            try:
                city.unlink()
                city_imds.unlink()
                total_deleted += 1
                _logger.info(
                    "DIVIPOLA cleanup: borrada ciudad id=%s y %s ir.model.data",
                    city.id,
                    len(city_imds),
                )
            except Exception as e:
                _logger.exception(
                    "DIVIPOLA cleanup: ERROR borrando ciudad id=%s: %s",
                    city.id,
                    e,
                )

        _logger.info(
            "DIVIPOLA cleanup: FIN. procesadas=%s, eliminadas=%s, sin_canónica=%s",
            len(cities),
            total_deleted,
            total_without_canon,
        )

        return self._notify_divipola(
            "DIVIPOLA l10n_co_bases: procesadas %s, eliminadas %s, sin canónica %s. "
            "Revisa el log para más detalle."
            % (len(cities), total_deleted, total_without_canon)
        )

    def _notify_divipola(self, message, notif_type="success"):
        """Muestra notificación en pantalla tras ejecutar el botón."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'DIVIPOLA l10n_co_bases',
                'message': message,
                'type': notif_type,  # success | warning | danger
                'sticky': False,
            },
        }