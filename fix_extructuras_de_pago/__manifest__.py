# -*- coding: utf-8 -*-
{
    'name': "fix_extructuras_de_pago",

    'summary': "Promedios, auxilios y contabilizacion personalizada de nomina, agrega campos para poder agrupar estructuras salariales",

    'author': "My Company",
    'license': 'LGPL-3',
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.2.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_payroll','hr_contract', 'account','hr', 'hr_payroll_account'],

    # always loaded
    'data': [
        "security/security.xml",
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/hr_administradora.xml',
        'views/hr_centrocostos.xml',
        'views/hr_employee.xml',
        'views/hr_contract.xml',
        'views/hr_payslip.xml',
        'views/hr_tipo.xml',
        'views/menu.xml',
        'views/res_company.xml',
        'views/templates.xml',
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
