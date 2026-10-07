# -*- coding: utf-8 -*-
{
    "name": "DS Advanced Logistics",
    "summary": "Herramientas avanzadas de logística, inventario y costos para Di'Silvio",
    "description": """
        Módulo paraguas para desarrollos avanzados de logística:
        - Ajuste de Inventario Retroactivo con borradores persistentes
        - (Próximamente) Herramientas de compras, costos y más
    """,
    "author": "Di'Silvio / Jose Martinez",
    "website": "https://www.disilvio.com",
    "category": "Inventory/Inventory",
    "version": "18.0.2.0.0",
    "depends": [
        "stock",
        "stock_account",
        "hr",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "wizard/ds_inventory_adjustment_confirm_views.xml",
        "wizard/ds_inventory_adjustment_import_views.xml",
        "views/ds_inventory_adjustment_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
