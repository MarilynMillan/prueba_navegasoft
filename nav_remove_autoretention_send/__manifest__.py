# -*- coding: utf-8 -*-
{
    "name": "NAV - Remover autorretención del envío de facturas",
    "summary": "Oculta impuestos marcados (autorretención) en PDF y evita adjuntos XML/ZIP en el envío de factura.",
    "version": "18.0.1.1.4",
    "author": "Navegasoft",
    "website": "https://navegasoft.co",
    "category": "Accounting",
    "license": "OEEL-1",
    'depends': [
        'account',
        'account_edi',
        'l10n_co_dian',      
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_tax_views.xml",
        "views/report_invoice_hide_autoretention.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
}
