# -*- coding: utf-8 -*-
# Part of Softhealer Technologies
{
    "name": "Inventory Adjustment Backdate",
    "author" : "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Warehouse",
    "summary": "Backdate Remarks Backdate Stock Adjustment Backdate Inventory Adjustment Backdate Stock Moves Backdate Journal Backdate Journal Entry Backdate Odoo Inventory Adjustment Date Inventory Adjustment Force Date Force Date Inventory Adjustment Back Dated Stock Adjustment Date Stock Adjustment Back Dated Inventory Force Date Inventory Backdate Inventory Adjustment Backdated Inventory Adjustment Force Date Stock Adjustment Back Dated Stock Force Date Stock Backdate Stock Adjustment Backdated Stock Adjustment Backdate Remarks Stock Backdate Remarks inventory backdate inventory adjustment backdate Change effective date change effective dates effective date changes in effective date effective date change in inventory adjustment",    

    "description": """ This module helps you make changes to your inventory records with past dates. You can specify a custom date and add notes for the adjustment. These details will be recorded not only in the inventory adjustments but also in related records like stock moves, product moves, and stock valuation.""",
    "version": "0.0.2",
    "depends": ["stock","stock_account"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/stock_move_views.xml",
        "views/stock_quant_views.xml",
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "images": ["static/description/background.png",],
    "license": "OPL-1",
    "price": 14.8,
    "currency": "EUR"
}
