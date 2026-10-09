from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    dian_grouping_scope = fields.Selection(
        selection=[
            ("global", "Global"),
            ("journal", "By journal"),
        ],
        string="Grouping scope",
        default="global",
        required=True,
    )
    dian_grouping_journal_ids = fields.Many2many(
        "account.journal",
        "res_company_dian_grouping_journal_rel",
        "company_id",
        "journal_id",
        string="Journals with grouping",
        domain="[('type', '=', 'sale')]",
    )
    dian_grouping_product_mode = fields.Selection(
        selection=[
            ("variant", "By variant"),
            ("template", "By template"),
        ],
        string="Product grouping mode",
        default="variant",
        required=True,
    )
