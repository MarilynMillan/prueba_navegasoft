{
    'name': 'Screen POS Custom',
    'version': '4.0',
    'description': 'Screen POS Custom - Combo nativo Odoo 18',
    'summary': 'Muestra items del combo agrupados en la pantalla de preparación, manteniendo el orden original de comandeo. Encabezado personalizado con MESA, nombre de zona y mesero.',
    'author': 'MyCompany',
    'license': 'LGPL-3',
    'category': 'point_of_sale',
    'depends': [
        'point_of_sale',
        'pos_preparation_display',
        'pos_restaurant_preparation_display',
        'pos_table_time_waiter_tracker',
    ],
    'data': [],
    'assets': {
        'pos_preparation_display.assets': [
            'screen_order_custom/static/src/app/**/*',
        ],
    },
}
