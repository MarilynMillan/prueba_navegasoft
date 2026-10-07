# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
{
    'name'              :   'Pos Restaurant Restrictions and Validations',
    'version'           :   '1.0.1',
    "author"            :   "Webkul Software Pvt. Ltd.",
    'category'          :   'Point of Sale',
    'sequence'          :   1,
    'summary'           :   '''The Odoo POS Restaurant Restrictions and Validations Module enhances POS security by restricting employees from deleting order lines or entire orders without manager approval or password/PIN authentication. It also requires PIN authentication for closing POS sessions, preventing unauthorized closures. Additionally, the module tracks and logs all restricted actions for review in the Odoo back office, ensuring accountability and oversight.|Restaurant Restriction|Restriction Validation|Restriction|Validation|Pos Restriction ''',
    'description'       :   """The Odoo POS Restaurant Restrictions and Validations Module enforces restrictions on deleting order lines and entire orders with manager approval or PIN authentication. It requires PIN entry for closing POS sessions and logs all restricted actions for review in the back office.""",
    'depends'           :   ['point_of_sale','pos_restaurant','hr'],
    "live_test_url"     :   "http://odoodemo.webkul.com/?module=pos_restaurant_restiction_and_validation&custom_url=/pos/auto",
    'website'           :   'https://store.webkul.com ',
    'demo'              :   [
                                'demo/demo.xml'
                            ],
    'data'              :   [
                                'security/ir.model.access.csv',
                                'views/pos_config_view.xml',
                                'views/pos_manager_approval_view.xml',
                            ],
    'installable'       :   True,
    'application'       :   True,
    'assets'            :   {
                                'point_of_sale._assets_pos': [
                                    'pos_restaurant_restiction_and_validation/static/src/screens/popUps/deny_popUp.js',
                                    'pos_restaurant_restiction_and_validation/static/src/screens/popUps/deny_popUp.xml',
                                    'pos_restaurant_restiction_and_validation/static/src/app/delete_by_manager.js',
                                    'pos_restaurant_restiction_and_validation/static/src/app/session_close_by_manager.js',
                                    'pos_restaurant_restiction_and_validation/static/src/app/decrease_quantity_by_manager.js',
                                ],
                            },
    "images"            :   ['static/description/Banner.png'],
    'license'           :   'Other proprietary',
    "price"             :    49,
    "currency"          :   "USD",
    "pre_init_hook"     :   "pre_init_check",
}
