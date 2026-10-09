from odoo import models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    def _check_edi_line_tax_required(self):
        if self.move_id.company_id.country_id.code == 'CO':
            # Solo tratamos como recompensa si el valor es negativo
            if self.price_subtotal >= 0:
                return super()._check_edi_line_tax_required()

            rewards = self.env['loyalty.reward'].sudo().search([
                ('active', '=', True),
                ('discount_line_product_id', '=', self.product_id.id),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            has_program = False
            program = self.env['loyalty.program'].sudo().search([
                ('active', '=', True),
                ('payment_program_discount_product_id', '=', self.product_id.id),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if program and program.payment_program_discount_product_id.id == self.product_id.id:
                has_program = True

            return not (rewards or has_program)
        return super(AccountMoveLine, self)._check_edi_line_tax_required()