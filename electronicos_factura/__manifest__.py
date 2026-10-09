# -*- coding: utf-8 -*-
{
    'name': "electronicos_factura",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Agrega funcionalidad de enviar documentos electronicos a la factura
    """,

    'author': "ALAN",
    'website': "http://www.navegasoft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','base_electronicos','l10n_co_bases'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/ir_sequence_view.xml',
        'views/account_journal_view.xml',
    ],
    # only loaded in demonstration mode
    'license': 'OPL-1',
    'demo': [
        'demo/demo.xml',
    ],
}