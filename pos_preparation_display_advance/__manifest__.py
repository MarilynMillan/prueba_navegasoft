{
    'name': 'Pos Preparation Display Advance',
    'version': '3.0',
    'description': 'Configuración avanzada de pantallas de preparación: categorías por POS, '
                   'pantallas tipo mesero con flujo encadenado cocina → meseros, '
                   'confirmación antes de enviar a Listo, categorías propias para '
                   'aislamiento de interacciones entre pantallas.',
    'summary': 'Categorías por POS + Pantallas de Mesero + Confirmación Listo + Owned Categories.',
    'author': 'Di Silvio Trattoria',
    'license': 'LGPL-3',
    'category': 'point_of_sale',
    'depends': [
        'pos_preparation_display',
        'pos_restaurant_preparation_display',
        'screen_order_custom',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/preparation_display_view.xml',
    ],
    'assets': {
        'pos_preparation_display.assets': [
            'pos_preparation_display_advance/static/src/app/components/order/order.js',
            'pos_preparation_display_advance/static/src/app/components/order/order.xml',
            'pos_preparation_display_advance/static/src/app/components/orderline/orderline.js',
        ],
    },
    'installable': True,
    'application': False,
}
