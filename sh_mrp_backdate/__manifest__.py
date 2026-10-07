# -*- coding: utf-8 -*-
# Part of Softhealer Technologies

{
    "name": "MRP Backdate | Change Effective Date | Manufacturing Order Backdate",
    "author" : "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Manufacturing",
    "summary": "Backdate and Remarks Backdate Remarks in Odoo Force Date manufacturing backdate Confirmation Backdate Mass Confirmation Backdate Mass Backdate confirm date confirm past date BOM Backdate old date Work Order Backdate MRP order backdate Change effective date change effective dates effective date changes in effective date effective date change mrp effective date change mrp effective date change Manufacturing effective date change stock move effective date change product move effective date change in mrp effective date change in manufacturing Odoo",
    "description": """In odoo, while you confirm the manufacturing orders it will take the current date as confirmation date and you can not change the date after confirming it so our module is useful for confirm MRP orders with selected confirmation backdate. You can put a custom backdate and remarks in the MRP orders. You can mass assign backdate in one click. When you mass assign backdate, it asks for remarks in the mass assign wizard. This selected date and remarks are also reflects in the stock moves, product moves & journal entries.""",
    "version": "0.0.2",
    "depends": ["stock_account","mrp","mrp_account"],
    "data": [

        'security/ir.model.access.csv',
        'security/sh_mrp_backdate_groups.xml',
        'data/mrp_production_data.xml',
        'wizard/sh_mrp_backdate_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_move_views.xml',
        'views/stock_move_line_views.xml',
    ],

    "auto_install":False,
    "installable": True,
    "application" : True,
    "images": ["static/description/background.png",],
    "license": "OPL-1",
    "price": 20,
    "currency": "EUR"
}
