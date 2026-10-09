# -*- coding: utf-8 -*-
{
    'name': "Consolidado de nómina",
    'description': 'Consolidado de nómina de acuerdo a la fecha seleccionada',
    'summary': 'Módulo consolidado de nómina',
    'author': "Navegasoft",
    'license': 'LGPL-3',
    'website': "http://www.navegasoft.com",
    'category': 'Human Resources/Employees',
    'version': '18.0.1.0.1',
    'depends': [
        'hr', 
        'hr_payroll', 
        'base',
    ],
    'application': False,
    'data': [
        'security/ir.model.access.csv',
        'views/consolidated_payroll_views.xml',
        'views/consolidated_payroll_menu.xml',
        'views/hr_payslip_views.xml',
        'data/consolidated_payroll_sequence.xml',
    ]
}
