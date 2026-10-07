# Part of Softhealer Technologies.
{
    "name": "Point Of Sale Screen Lock",
    "author": "Softhealer Technologies",
     'version': '18.0.1.0.0',
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "point of sale",
    "license": "OPL-1",
    "summary": "Point Of Sale Screen Auto Lock POS Auto Lock POS Screen Auto Lock Point Of Sale Automatic Screen Lock POS Screen Lock Pos Lock Screen Automatic Pos Lock Screen Manual POS Session Lock point of sale lock POS Lock Auto POS Lock Odoo Point Of Sale Auto Lock",
    "description": """The module allows the POS user to set auto-lock for the POS screen. You can secure the POS screen by 2 methods,

1) Using Time-Interval: Here you have to set a time for the auto-lock screen so after that time interval POS screen is automatically locked and after that, you can unlock the POS screen by clicking on the button.

2) Using Password: Here you have to set a password for unauthorized access. So authorized persons (POS users/cashiers) can unlock the POS screen by their password.""",
    "version": "0.0.1",
    "depends": ["point_of_sale", "pos_hr"],
    "application": True,
    "data": [
        'views/res_config_settings.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
           'sh_pos_auto_lock/static/src/**/*',
        ],
    },
    "auto_install": False,
    "installable": True,
    "images": ["static/description/background.png", ],
    "price": 10,
    "currency": "EUR"
}
