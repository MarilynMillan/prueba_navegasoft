# -*- coding: utf-8 -*-
{
    'name': "Colombia: Eventos RADIAN",

    'summary': """
            Eventos RADIAN para la localización colombiana directo con la DIAN
        """,
    'description': """
        Porta las funcionalidades de Odoo 19 (l10n_co_dian) a Odoo 18:
        - Eventos RADIAN (ApplicationResponse):
            030 - Acuse de recibo
            031 - Reclamo
            032 - Recibo del bien y/o prestación del servicio
            033 - Aceptación expresa
            034 - Aceptación Tácita (Aceptación por el emisor)
        - Documento de Soporte (Tipo 05 / 95)
        - AttachedDocument con historial de eventos
        - CRON para actualización automática de estados RADIAN
        - Proceso de certificación DIAN
    """,
    'author': 'MI ERP APP',
    'company': 'GRUPO MI ERP SAS',
    'maintainer': 'MI ERP APP',
    'website': 'https://www.mi-erp.app',
    'category': 'Accounting/Localizations/EDI',
    'version': '18.0.2.0.0',
    'depends': [
        'base',
        'l10n_co_dian',
        'account',
        'account_edi_ubl_cii',
        'l10n_co_edi',
        'certificate',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/product_product.xml',
        'wizard/l10n_co_dian_claim_wizard.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
        'data/ir_cron.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'images': [
        'static/description/thumbnail.png',
    ],
    "license": "Other proprietary",
    "price": 200,
    "currency": "USD",
}
