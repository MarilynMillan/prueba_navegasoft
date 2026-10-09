{
    'name': "medios_magneticos",
    'summary': "Generación de medios magnéticos para DIAN.",
    'description': "Módulo de medios magnéticos para Odoo.",
    'author': "Navegasoft",
    'website': "https://www.navegasoft.com",
    'category': 'Accounting/Accounting',
    'version': "18.0.1.0.0",
    'depends': ['base','account','report_xlsx','l10n_co_reports'], #,'date_range'
    'data': [
        'security/ir.model.access.csv',
        "wizard/open_tax_balances_view.xml",
        "wizard/configurar_medios_view.xml",
        'views/views.xml',
        'views/res_company_view.xml',
        'views/templates.xml',
        'views/account_account.xml',
        'views/menu_reorganization.xml'],
    'license': 'OPL-1',
    'demo': [
        'demo/demo.xml',
    ],
}
