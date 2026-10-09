{
    "name": "DIAN - Restricción de líneas de factura",
    "description": "Agrupa líneas de factura por variante para DIAN e impresión PDF.",
    "summary": "DIAN - Restricción de líneas de factura",
    "author": "Navegasoft",
    "website": "http://www.navegasoft.com",
    "version": "18.0.2.0.0",
    "depends": [
        "l10n_co_dian",
        "account",
    ],
    "data": [
        "views/account_invoice_views.xml",
        "views/res_config_settings_views.xml",
        "views/report_invoice.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
}
