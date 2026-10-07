# -*- coding: utf-8 -*-
{
    'name': 'Fix POS Merge/Split Order Kitchen',
    'summary': 'Evita reenvíos y cancelaciones fantasma en cocina al fusionar o dividir mesas',
    'description': """
        Fix 1 - MERGE: Al fusionar mesas, evita que los productos ya enviados
        aparezcan como cancelados o se reenvíen a cocina.
        
        Fix 2 - SPLIT: Al dividir una orden y luego comandar algo nuevo en la
        orden dividida, evita que los productos ya enviados se reenvíen como
        nuevos a cocina. Crea pdis_lines silenciosamente sin notificar
        a las pantallas.
    """,
    'author': 'Divitas',
    'category': 'Point of Sale',
    'version': '18.0.6.0.0',
    'depends': ['pos_restaurant', 'pos_preparation_display'],
    'assets': {
        'point_of_sale._assets_pos': [
            'fix_pos_merge_kitchen/static/src/overrides/pos_store_patch.js',
        ],
    },
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
