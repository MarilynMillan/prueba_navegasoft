# -*- coding: utf-8 -*-
{
    'name': 'POS Restaurant Table Show Seated Time | Waiter Name | Order Amount',
    'summary': """Pos Restaurant Table Time Counter Waiter Tracker Pos Restaurant Table Time Counter Show Seated Time on Table pos Restaurant waiter name pos Restaurant seated time pos Restaurant order amount pos Restaurant waiter name pos Restaurant cashier name pos Restaurant table waiter name pos Restaurant table seated time pos Restaurant table control pos Restaurant table managemnet pos table access pos Restaurant order amount show pos pos Restaurant pos Restaurant kitchen pos Restaurant waiter pos Restaurant table seated time pos Restaurant Table Timer pos Restaurant Waiter Assignment POS Table Time & Waiter Tracker """,
    'description': """Pos Restaurant Table Time seated time Counter Waiter Tracker and order amount""",
    'version': '18.0.0.0',
    'depends': ['base', 'pos_restaurant'],
    'data': [
        'views/pos_order_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_table_time_waiter_tracker/static/src/js/payment_screen.js',
            'pos_table_time_waiter_tracker/static/src/js/actionpad_widget.js',
            'pos_table_time_waiter_tracker/static/src/js/floor_screen.js',
            'pos_table_time_waiter_tracker/static/src/xml/floor_screen.xml',
            'pos_table_time_waiter_tracker/static/src/css/floor_screen.css',
        ],
    },
    'category': 'Point of Sale',
    'author': 'Khaled Hassan',
    'website': "https://apps.odoo.com/apps/modules/browse?search=Khaled+hassan",
    'license': 'OPL-1',
    'images': ['static/description/main_screenshot.png'],
    'price': 75,
    'currency': 'USD',
    'installable': True,
    'application': False,
    'auto_install': False,
}
