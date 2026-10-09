# -*- coding: utf-8 -*-
{
    'name': "base_electronicos",

    'summary': """
        Base para modulos de documentos electronicos""",

    'description': """
        Base para modulos de documentos electronicos
    """,

    'author': "Alan",
    'website': "http://www.navegasoft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],
    'license': 'OPL-1',
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}