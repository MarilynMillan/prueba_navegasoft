from odoo import Command
from odoo.tests.common import TransactionCase


class TestDianGroupingLogic(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.unit_uom = cls.env.ref("uom.product_uom_unit")
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        ) or cls.env["account.journal"].create({
            "name": "Test Sale Journal",
            "code": "TSAL",
            "type": "sale",
            "company_id": cls.company.id,
        })

        attribute = cls.env["product.attribute"].create({"name": "Test Color"})
        red = cls.env["product.attribute.value"].create(
            {"name": "Red", "attribute_id": attribute.id}
        )
        blue = cls.env["product.attribute.value"].create(
            {"name": "Blue", "attribute_id": attribute.id}
        )
        template = cls.env["product.template"].create(
            {
                "name": "Template Grouping Product",
                "type": "consu",
                "uom_id": cls.unit_uom.id,
                "uom_po_id": cls.unit_uom.id,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set([red.id, blue.id])],
                        }
                    )
                ],
            }
        )
        variants = template.product_variant_ids
        cls.variant_a = variants[0]
        cls.variant_b = variants[1]

    def _new_move(self):
        return self.env["account.move"].new(
            {
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "journal_id": self.sale_journal.id,
            }
        )

    def _line_commands(self):
        return [
            Command.create(
                {
                    "name": "Line A",
                    "product_id": self.variant_a.id,
                    "quantity": 1.0,
                    "price_unit": 100.0,
                    "discount": 0.0,
                    "product_uom_id": self.unit_uom.id,
                }
            ),
            Command.create(
                {
                    "name": "Line B",
                    "product_id": self.variant_b.id,
                    "quantity": 2.0,
                    "price_unit": 100.0,
                    "discount": 0.0,
                    "product_uom_id": self.unit_uom.id,
                }
            ),
        ]

    def test_grouping_scope_by_journal(self):
        self.company.dian_grouping_scope = "journal"
        self.company.dian_grouping_journal_ids = [Command.clear()]
        move = self._new_move()
        self.assertFalse(move._is_dian_grouping_active())

        self.company.dian_grouping_journal_ids = [Command.set([self.sale_journal.id])]
        move = self._new_move()
        self.assertTrue(move._is_dian_grouping_active())

    def test_grouping_keys(self):
        self.company.dian_grouping_scope = "global"
        move = self._new_move()
        move.invoice_line_ids = self._line_commands()
        self.assertEqual(len(move._nav_grouping_keys_for_dian()), 2)

    def test_grouped_lines_for_report(self):
        self.company.dian_grouping_scope = "global"
        move = self._new_move()
        move.invoice_line_ids = self._line_commands()
        grouped_lines = move._nav_get_grouped_invoice_lines_for_pdf(
            self.env["invoice.line.grouped"]
        )
        self.assertEqual(len(grouped_lines), 2)
