{
    'name': 'Colombia - Impuestos',
    'category': 'Localization',
    'version': '18.0.0.0.3',
    'author': 'Grobsistemas',
    'license': 'OPL-1',
    'maintainer': 'gerente@grobsistemas.com',
    'website': 'http://navegasoft.com',
    'summary': 'Colombian Taxes: Invoice Module',
    'images': ['images/'],
    'description': """
Colombia Impuestos:
======================
    * This module calculates some Colombian taxes that have to apply
    * First tax: withholding tax, which is calculated by  the untaxed amount and calculated with the total amount
    """,
    'depends': [
        'account',
        'sale',
        'purchase',
        'l10n_co'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/l10n_co_tax_extension.xml',
        'views/report_invoice.xml',
        'views/ir_sequence_view.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml'
    ],
}
