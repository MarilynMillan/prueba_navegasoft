{
    "name": "Ticket personalizado para PdV",
    "summary": "Impresión de Ticket personalizado en TdV",
    "author": "RicardoTeranNet",
    "website": "https://www.ricardoteran.net",
    "contributor": ["https://github.com/VizMan0616"],
    "license": "LGPL-3",
    "category": "Pos/Accounting/Sales",
    "version": "18.0.1.3.4",
    "depends": ["point_of_sale", "pos_restaurant", "l10n_co_dian"],
    "data": [
        # 'security/ir.model.access.csv',
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_custom_ticket/static/src/**/*",
        ]
    },
}
