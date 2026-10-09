{
    'name': 'Dotación_employee',
    'version': '18.0.2.0.1',
    'summary': 'Integra las entregas de dotación con la nómina de empleados',
    'category': 'account',
    'author': 'Navegasoft ,Colaborador:Ing.Marilynmillan.',
    'depends': [
        'base',
        'stock',
        'hr',
        'hr_payroll',
        'hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking.xml',
        'views/product_category.xml',
        'views/hr_employee_dotacion.xml',
    ],
    'license': 'OPL-1',
    'application': True,
}
