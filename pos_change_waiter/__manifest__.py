# -*- coding: utf-8 -*-
{
    'name': 'POS Cambiar Mesero',
    'summary': 'Cambio de mesero en POS con PIN obligatorio y auditoría en chatter',
    'description': """
        Módulo para Di'Silvio Trattoria - DIVITIAS SAS
        
        Funcionalidades:
        - Botón "Cambiar Mesero" en Actions del POS (solo managers)
        - Verificación PIN obligatoria del empleado que autoriza
        - Auditoría completa en el chatter de pos.order:
          * Mesero anterior
          * Mesero nuevo
          * Quién autorizó el cambio
          * Fecha y hora exacta
    """,
    'version': '18.0.2.0.0',
    'depends': ['pos_restaurant', 'pos_hr'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_change_waiter/static/src/js/change_waiter_button.js',
            'pos_change_waiter/static/src/xml/change_waiter_button.xml',
            'pos_change_waiter/static/src/css/change_waiter.css',
        ],
    },
    'category': 'Point of Sale',
    'author': "Di'Silvio Trattoria - DIVITIAS SAS",
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
