{
    'name': 'Kardex - Reporte de Existencias',
    'version': '18.0.1.0.0',
    'author': 'DIVITIAS SAS',
    'category': 'Inventory/Reporting',
    'summary': 'Kardex completo de inventario con entradas y salidas clasificadas',
    'description': """
        Reporte Kardex de inventario con:
        - Cantidad Inicial (existencias a fecha inicio)
        - Entradas: Compras/Recepciones, Manufactura, Ajustes de Inventario
        - Salidas: Ventas, Manufactura, Desperdicios, Ajustes de Inventario
        - Cantidad Final
        - Agrupado por categoría de producto
        - Exportación a Excel (xlsx)
        - Consultas SQL optimizadas (read_group)
    """,
    'depends': ['stock', 'purchase', 'sale_management', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/kardex_report_wizard_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
