#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
{
  "name"                 :  "POS Combo Products",
  "summary"              :  """ POS Combo Products enable you to configure and create
                            product combos in Odoo POS. This Odoo app permits you to configure categories,minimum and maximum combo options, and inventory management in the Odoo backend. You can further choose from a grid or list view to show the product combo popup in the Odoo POS frontend.POS Combo Product|POS Combination Products|POS Extra Product|POS Sides|Buy Two|Combo POS|Combo Products|pos combo|POS Combo|Combo Items|POS Combo Items|Buy One|Buy Each|Each At|Food Combo|product combo in odoo""",
  "category"             :  "Point of Sale",
  "version"              :  "1.0.1",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/odoo-pos-combo-products.html",
  "description"          :  """ POS Combo Product , POS Combination Products , POS Extra Product , POS Sides , Buy Two , Combo POS , Combo Products , pos combo , POS Combo , Combo Items , POS Combo Items , Buy One Buy Each , Each At , Food Combo , product combo in odoo """,
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=pos_combo_products&custom_url=/pos/auto",
  "depends"              :  [
                             'point_of_sale',
                            ],
  "data"                 :  [               
                              'security/ir.model.access.csv',   
                              'views/pos_config.xml',
                              'views/pos_combo_products.xml',
                            ],
  "demo"                 :  ['demo/demo.xml'],
  "assets"               :  {
                              'point_of_sale._assets_pos': [
                                "/pos_combo_products/static/src/overrides/popup/popup.xml",
                                "/pos_combo_products/static/src/overrides/popup/popup.js",
                                "/pos_combo_products/static/src/overrides/screen/pos.xml",
                                "/pos_combo_products/static/src/overrides/screen/screens.js",
                                "/pos_combo_products/static/src/overrides/models.js",
                                "/pos_combo_products/static/src/overrides/pos.css",
                                'web/static/lib/jquery/jquery.js',
                              ],
                            },
  "images"               :  ['static/description/banner.png'],
  "qweb"                 :  ['static/src/xml/pos.xml'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
