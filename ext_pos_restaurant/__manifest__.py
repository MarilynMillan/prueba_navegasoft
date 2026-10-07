{
    'name': 'Extensión POS Restaurant',
    'summary': 'Extensión para la integración con POS Restaurant',
    'description': """
    Extensión para la integración con POS Restaurant.
    """,
    "version": "1.0.0",
    'author': "Navegasoft SAS",
    'website': "https://navegasoft.com",
    'assets': {
        'point_of_sale._assets_pos': [
            'ext_pos_restaurant/static/src/**/*',
        ],
    },
    'depends': ['pos_restaurant', 'point_of_sale'],
    'installable': True,
    'auto_install': False,
    'license': 'Other proprietary'
}