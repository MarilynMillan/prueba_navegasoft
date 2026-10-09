{
    'name': "electronicos_nomina",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Agrega funcionalidad para enviar documento electronico nomina
    """,

    'author': "Alan",
    'website': "http://www.navegasoft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': "18.0.1.0.0",

    # any module necessary for this one to work correctly
    'depends': ['base','base_electronicos','hr_payroll','l10n_co_bases','consolidated_payroll'], #,'consolidated_payroll'

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_message.xml',
        'data/data.xml',
        'views/views.xml',
       # 'views/templates.xml',
        'views/consolidated_payroll.xml',
    ],
    # only loaded in demonstration mode
    'license': 'OPL-1',
    'demo': [
        'demo/demo.xml',
    ],
}