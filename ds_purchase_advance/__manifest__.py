# -*- coding: utf-8 -*-
{
    "name": "DS Purchase Advance",
    "summary": "Requisiciones de Compra por Sede + Actualización automática de precios de proveedor",
    "description": """
        Flujo avanzado de compras para Di'Silvio:

        1. REQUISICIONES DE COMPRA POR SEDE
           - Las sedes crean requisiciones de productos sin proveedor
           - El área de compras genera OC desde las requisiciones
           - Trazabilidad completa entre requisiciones y OC
           - Control de cantidades pendientes y progreso

        2. ACTUALIZACIÓN AUTOMÁTICA DE PRECIOS DE PROVEEDOR
           - Al confirmar una OC, se actualiza el precio en la lista
             de precios del proveedor (product.supplierinfo)
           - Solo la compra más reciente actualiza el precio
           - Conversión automática de moneda y UdM
    """,
    "author": "Di'Silvio / Jose Martinez",
    "website": "https://www.disilvio.com",
    "category": "Inventory/Purchase",
    "version": "18.0.1.1.0",
    "depends": [
        "purchase",
        "stock",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/ds_purchase_requisition_views.xml",
        "views/purchase_order_views.xml",
        "wizard/ds_requisition_load_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
