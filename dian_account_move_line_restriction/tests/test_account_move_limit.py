from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountMoveGroupedLinesLimit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        ) or cls.env["account.journal"].create({
            "name": "Test Sale Journal",
            "code": "TSAL",
            "type": "sale",
            "company_id": cls.company.id,
        })

    def _new_move(self):
        return self.env["account.move"].new({
            "move_type": "out_invoice",
            "company_id": self.company.id,
            "journal_id": self.sale_journal.id,
        })

    def test_get_grouped_lines_limit_from_config(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "dian_account_move_line_restriction.grouped_lines_limit", "125"
        )
        move = self._new_move()
        self.assertEqual(move._get_grouped_lines_limit(), 125)

    def test_check_grouped_lines_limit_uses_default_100(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", "dian_account_move_line_restriction.grouped_lines_limit")]
        ).unlink()
        move = self._new_move()
        move.total_grouped_lines_by_variant = 101

        with self.assertRaises(UserError):
            move._nav_check_grouped_line_limit_for_dian()

    def test_check_grouped_lines_limit_allows_when_under_configured_limit(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "dian_account_move_line_restriction.grouped_lines_limit", "150"
        )
        move = self._new_move()
        move.total_grouped_lines_by_variant = 120

        move._nav_check_grouped_line_limit_for_dian()
