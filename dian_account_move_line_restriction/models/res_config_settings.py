from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dian_grouping_scope = fields.Selection(
        related="company_id.dian_grouping_scope",
        readonly=False,
        string="Grouping scope",
    )
    dian_grouping_journal_ids = fields.Many2many(
        related="company_id.dian_grouping_journal_ids",
        readonly=False,
        string="Journals with grouping",
    )
    dian_grouping_product_mode = fields.Selection(
        related="company_id.dian_grouping_product_mode",
        readonly=False,
        string="Product grouping mode",
    )
    grouped_lines_limit = fields.Integer(
        string="Grouped Lines Limit",
        config_parameter="dian_account_move_line_restriction.grouped_lines_limit",
        default=100,
    )
