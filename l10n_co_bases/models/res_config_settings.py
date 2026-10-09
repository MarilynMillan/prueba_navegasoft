from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    comment_text_with_format = fields.Boolean(string="Comment text with format")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            comment_text_with_format=self.env['ir.config_parameter'].sudo().get_param('l10n_co_bases.comment_text_with_format')
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('l10n_co_bases.comment_text_with_format', self.comment_text_with_format)

