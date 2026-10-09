# -*- coding: utf-8 -*-
{
    'name': "electronicos_pos",
    'summary': "Restricciones POS para facturación electrónica.",
    'description': "Extensión POS para reglas de facturación electrónica en Colombia.",
    'author': "Navegasoft",
    'license': 'LGPL-3',
    'website': "https://navegasoft.com",
    'category': 'Point of Sale',
    'version': '18.0',
    'depends': ['base','point_of_sale'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'views/pos_config.xml',
    ],'assets':{
        'point_of_sale.assets': [
            '/electronicos_pos/static/src/js/restriction_pos.js',  # no borrar!
        ],
        
    },
    'demo': [
        'demo/demo.xml',
    ],
}
