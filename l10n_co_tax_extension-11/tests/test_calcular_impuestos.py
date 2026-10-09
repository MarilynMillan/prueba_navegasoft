from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests.common import TransactionCase


class TestCalcularImpuestos(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner Test Taxes',
        })

        cls.journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('type', '=', 'sale'),
        ], limit=1)

        cls.income_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('deprecated', '=', False),
        ], limit=1)

        if not cls.income_account:
            cls.income_account = cls.env['account.account'].create({
                'name': 'Income Test Account',
                'code': 'X999999',
                'account_type': 'income',
            })

        cls.fp = cls.env['account.fiscal.position'].create({
            'name': 'FP Test Taxes',
            'company_id': cls.company.id,
        })

        cls.tax = cls.env['account.tax'].create({
            'name': 'Tax Test 5%',
            'amount_type': 'percent',
            'amount': 5.0,
            'type_tax_use': 'sale',
            'company_id': cls.company.id,
            'country_id': cls.company.account_fiscal_country_id.id,
        })

        cls.env['account.fiscal.position.base.tax'].create({
            'position_id': cls.fp.id,
            'tax_id': cls.tax.id,
        })

        today = fields.Date.context_today(cls.env.user)
        cls.env['account.base.tax'].create({
            'tax_id': cls.tax.id,
            'start_date': today - timedelta(days=1),
            'end_date': today + timedelta(days=1),
            'amount': 0.0,
        })

    def _create_move(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'fiscal_position_id': self.fp.id,
            'invoice_line_ids': [Command.create({
                'name': 'Line Test',
                'quantity': 2,
                'price_unit': 100,
                'account_id': self.income_account.id,
                'tax_ids': [Command.clear()],
            })],
        })

    def test_calcular_impuestos_applies_base_and_taxes(self):
        move = self._create_move()

        move.calcularimpuestos()

        line = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')[:1]
        self.assertTrue(line)

        expected_base = line.quantity * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        self.assertEqual(line.base_retenciones, expected_base)
        self.assertIn(self.tax, line.tax_ids)

    def test_calcular_impuestos_is_idempotent_when_no_changes(self):
        move = self._create_move()
        move.calcularimpuestos()

        with patch.object(type(move), 'write', autospec=True, wraps=type(move).write) as mocked_write:
            move.calcularimpuestos()

        self.assertFalse(mocked_write.called, "calcularimpuestos should not write the move when there are no changes")

    def test_global_applicable_base_ignores_non_applicable_products(self):
        self.company.nav_rete_use_global_applicable_base = True
        self.tax.base_taxes.write({'amount': 500.0})

        product_applicable = self.env['product.product'].create({
            'name': 'Applicable Product',
            'nav_rete_is_applicable': True,
        })
        product_non_applicable = self.env['product.product'].create({
            'name': 'Non Applicable Product',
            'nav_rete_is_applicable': False,
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'fiscal_position_id': self.fp.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Applicable',
                    'quantity': 1,
                    'price_unit': 400,
                    'account_id': self.income_account.id,
                    'product_id': product_applicable.id,
                    'tax_ids': [Command.clear()],
                }),
                Command.create({
                    'name': 'Non Applicable',
                    'quantity': 1,
                    'price_unit': 1000,
                    'account_id': self.income_account.id,
                    'product_id': product_non_applicable.id,
                    'tax_ids': [Command.clear()],
                }),
            ],
        })
        move.calcularimpuestos()

        applicable_line = move.invoice_line_ids.filtered(lambda l: l.product_id == product_applicable)[:1]
        non_applicable_line = move.invoice_line_ids.filtered(lambda l: l.product_id == product_non_applicable)[:1]
        self.assertNotIn(self.tax, applicable_line.tax_ids)
        self.assertNotIn(self.tax, non_applicable_line.tax_ids)

        applicable_line.price_unit = 600
        move.calcularimpuestos()

        self.assertIn(self.tax, applicable_line.tax_ids)
        self.assertNotIn(self.tax, non_applicable_line.tax_ids)

    def test_threshold_applies_when_base_equals_threshold(self):
        self.company.nav_rete_use_global_applicable_base = False
        self.tax.base_taxes.write({'amount': 200.0})
        move = self._create_move()

        move.calcularimpuestos()

        line = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')[:1]
        self.assertEqual(line.base_retenciones, 200.0)
        self.assertIn(self.tax, line.tax_ids)

    def test_sale_line_manual_tax_override_on_new_line(self):
        sale_tax_19 = self.env['account.tax'].create({
            'name': 'VAT 19 Test',
            'amount_type': 'percent',
            'amount': 19.0,
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'country_id': self.company.account_fiscal_country_id.id,
        })
        sale_tax_5 = self.env['account.tax'].create({
            'name': 'VAT 5 Test',
            'amount_type': 'percent',
            'amount': 5.0,
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'country_id': self.company.account_fiscal_country_id.id,
        })
        product = self.env['product.product'].create({
            'name': 'Product SO Tax Override',
            'taxes_id': [Command.set([sale_tax_19.id])],
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
        })
        line = self.env['sale.order.line'].new({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })
        line._onchange_product_id()
        line._onchange_recompute_taxes_ui()
        self.assertIn(sale_tax_19, line.tax_id)

        line.tax_id = [Command.set([sale_tax_5.id])]
        line._onchange_mark_manual_tax_override()
        self.assertTrue(line.nav_manual_tax_override)

    def test_entry_line_computed_taxes_returns_empty_recordset(self):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal.id,
            'line_ids': [
                Command.create({
                    'name': 'Entry debit',
                    'account_id': self.income_account.id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'name': 'Entry credit',
                    'account_id': self.income_account.id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        })
        line = move.line_ids[:1]

        taxes = line._get_computed_taxes()

        self.assertEqual(taxes, self.env['account.tax'])
