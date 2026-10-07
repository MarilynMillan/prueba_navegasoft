{
    'name': 'Pos Access Right',
    'version': '18.0.2.0.0',
    'category': 'Sales/Point Of Sale',
    'summary': 'Derecho de accesos a POS',
    'description': """
        Derecho de accesos a POS
    """,
    'author': 'GreenApps',
    'company': 'Green Applications',
    'maintainer': 'GreenApps',
    'website': 'https://www.greenapplic.com',
    'depends': ['web','point_of_sale','pos_hr'],
    'data': [
        "views/res_config_settings.xml",
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            "/gpos_access_right/static/src/overrides/models/pos_store.js",
            "/gpos_access_right/static/src/app/screens/product_screen/product_screen.js",
            "/gpos_access_right/static/src/app/screens/ticket_screen/ticket_screen.js",
            "/gpos_access_right/static/src/app/screens/payment_screen.js",
            "/gpos_access_right/static/src/app/screens/ticket_screen/invoice_button.js",
            "/gpos_access_right/static/src/app/screens/control_buttons/control_buttons.js",
            'gpos_access_right/static/src/overrides/models/models.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

