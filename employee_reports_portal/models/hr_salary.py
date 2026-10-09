from odoo import fields, models, _

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    concept = fields.Many2one("hr.certified.concept", string="Concept")