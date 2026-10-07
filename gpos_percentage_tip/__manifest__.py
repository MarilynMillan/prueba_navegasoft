{
    'name': 'Pos Custom Tips',
    'version': '18.0.2.0.0',
    'summary': """Para aplicar un porcentaje fijo de propina""",
    'description': """Para aplicar un porcentaje fijo de propina a los pedidos.
Establecemos un porcentaje de propina que se aplicará a los pedidos.""",
    'author': 'GreenApps',
    'company': 'Green Applications',
    'maintainer': 'GreenApps',
    'website': 'https://www.greenapplic.com',
    'category': 'Point Of Sale',
    'depends': ['point_of_sale', 'pos_sale',],
    'data': {
        'views/res_config_settings_views.xml',
    },
    'assets': {
        'point_of_sale._assets_pos': [
            'gpos_percentage_tip/static/src/js/PaymentScreen.js',
            'gpos_percentage_tip/static/src/xml/PaymentScreen.xml',
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
