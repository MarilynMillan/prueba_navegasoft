# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
import logging

_logger = logging.getLogger(__name__)


class TestResCity(TransactionCase):

    def test_name_search(self):
        """
        Check name_search on res_city
        """
        country = self.env.ref('base.co')
        state = self.env['res.country.state'].create({
            'name': 'Antioquia test',
            'code': 'ANT-TEST',
            'country_id': country.id,
        })
        city = self.env['res.city'].create({
            'name': 'MEDELLÍN TEST',
            'code': '05001T',
            'state_id': state.id,
            'country_id': country.id,
        })

        ns_name = tuple(set(i[0] for i in self.env['res.city'].name_search('MEDELLÍN TEST')))
        ns_code = tuple(set(i[0] for i in self.env['res.city'].name_search('05001T')))

        self.assertIn(city.id, ns_name)
        self.assertIn(city.id, ns_code)
        
