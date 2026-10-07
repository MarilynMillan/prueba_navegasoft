# -*- coding: utf-8 -*-

{
    'name': 'POS Kitchen Direct Print y Template Comanda',
    'category': 'Point of Sale',
    'summary': 'Direct Kitchen Printing without iotBox and Custom XML Receipt Designs',
    'description': """
    POS Kitchen Receipt Customization
    =================================

    This module extends the Odoo Point of Sale (POS) application, enabling businesses to customize kitchen receipt with advanced XML designs. It offers a solution for restaurants, cafes, and other food service establishments looking to enhance their kitchen order management and printing processes.

    Key Features:
    -------------
    * **Custom Receipt Designs:** Allows the creation of custom kitchen receipt designs using XML, providing flexibility in how receipts are formatted, what information is included, and the overall presentation.
    * **Direct Printing with jPosBox:** Integrates with jPosBox, bypassing the need for the IoT Box and enabling direct printing from Odoo POS to your kitchen printers. This ensures faster, more reliable receipt printing and supports a wide range of printer models.
    * **Enhanced Kitchen Workflow:** By customizing the layout and details of kitchen receipts, kitchens can improve order accuracy, speed up preparation times, and enhance overall service quality.

    Ideal for any F&B business looking to streamline their kitchen operations and provide a customized experience, this module bridges the gap between standard POS functionality and the unique demands of kitchen management.
    """,
    'author': 'Dustin Mimbela',
    'version': '1.8',
    'depends': ['point_of_sale', 'pos_restaurant'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_kitchen_direct/static/src/js/**/*',
            'pos_kitchen_direct/static/src/xml/**/*'
        ],
    },
    "live_test_url":  "https://demo18.dustinmimbela.com",
    'price': 190.0,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    "license": "LGPL-3",
    "images":["static/description/banner.png"],
}
