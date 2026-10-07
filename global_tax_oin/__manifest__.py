# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright 2025 Odoo IT now <http://www.odooitnow.com/>
# See LICENSE file for full copyright and licensing details.
#
##############################################################################
{
    'name': 'Global Tax on Sale Order and Purchase Order',
    'category': 'Tax',
    'summary': 'Global Tax on SO orders and PO orders.',

    'version': '18.0.0.1',
    'description': """
Global Tax on Sale Order and Purchase Order
===========================================
This module provides the feature to calculate Global Tax on sale orders and
purchase orders.
        """,

    'author': 'Odoo IT now',
    'website': 'http://www.odooitnow.com/',
    'license': 'Other proprietary',

    'depends': [
        'sale_purchase',
        'sale_management',
        'account'
        ],

    'data': [
        'views/global_tax_view.xml'
    ],
    'images': ['images/OdooITnow_screenshot.png'],

    'price': 10.0,
    'currency': 'EUR',

    'installable': True,
    'application': False,
    'auto_install': False
}
