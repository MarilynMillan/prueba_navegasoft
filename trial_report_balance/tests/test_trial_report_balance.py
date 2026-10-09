# -*- coding: utf-8 -*-

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged("at_install", "post_install", "trial_report_balance")
class TestTrialReportBalance(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_1 = cls.env["res.partner"].create({
            "name": "Partner One",
            "vat": "P1-0001",
        })
        cls.partner_2 = cls.env["res.partner"].create({
            "name": "Partner Two",
            "vat": "P2-0001",
        })

        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.account_receivable = cls.company_data["default_account_receivable"]
        cls.account_payable = cls.company_data["default_account_payable"]
        cls.account_revenue = cls.company_data["default_account_revenue"]
        cls.account_expense = cls.company_data["default_account_expense"]

        cls._create_entry("2024-12-20", [
            (cls.account_receivable, cls.partner_1, 100.0, 0.0),
            (cls.account_revenue, False, 0.0, 100.0),
        ])
        cls._create_entry("2025-01-15", [
            (cls.account_receivable, cls.partner_1, 50.0, 0.0),
            (cls.account_revenue, False, 0.0, 50.0),
        ])
        cls._create_entry("2025-01-20", [
            (cls.account_receivable, cls.partner_2, 0.0, 30.0),
            (cls.account_revenue, False, 30.0, 0.0),
        ])
        cls._create_entry("2024-12-10", [
            (cls.account_expense, False, 80.0, 0.0),
            (cls.account_payable, cls.partner_1, 0.0, 80.0),
        ])
        cls._create_entry("2025-01-22", [
            (cls.account_expense, False, 20.0, 0.0),
            (cls.account_payable, cls.partner_1, 0.0, 20.0),
        ])

    @classmethod
    def _create_entry(cls, date, lines):
        move = cls.env["account.move"].create({
            "move_type": "entry",
            "date": date,
            "journal_id": cls.misc_journal.id,
            "line_ids": [
                Command.create({
                    "name": f"Line {index}",
                    "account_id": account.id,
                    "partner_id": partner.id if partner else False,
                    "debit": debit,
                    "credit": credit,
                })
                for index, (account, partner, debit, credit) in enumerate(lines, start=1)
            ],
        })
        move.action_post()

    def _run_partner_report(self, account_ids, partner_ids=None):
        partner_ids = partner_ids or self.env["res.partner"]
        wizard = self.env["balance.test.account"].create({
            "report_type": "partner",
            "view_type": "view",
            "date_start": "2025-01-01",
            "date_end": "2025-01-31",
            "account_account_ids": [Command.set(account_ids.ids)],
            "partner_ids": [Command.set(partner_ids.ids)],
        })
        wizard._search_data_move_line_third_party()
        rows = self.env["balance.test.account.partner"].search([
            ("code_account", "in", account_ids.mapped("code")),
        ])
        return rows

    def _run_general_report(self, account_ids):
        wizard = self.env["balance.test.account"].create({
            "report_type": "general",
            "view_type": "view",
            "date_start": "2025-01-01",
            "date_end": "2025-01-31",
            "account_account_ids": [Command.set(account_ids.ids)],
        })
        wizard._search_data_move_line_general()
        return self.env["balance.test.account.general"].search([
            ("code_account", "in", account_ids.mapped("code")),
        ])

    def test_partner_balance_uses_opening_and_period_for_receivable(self):
        rows = self._run_partner_report(self.account_receivable)
        summary_row = rows.filtered(lambda r: r.code_account == self.account_receivable.code and not r.third_party)
        self.assertEqual(len(summary_row), 1)
        self.assertAlmostEqual(summary_row.inicial_amount, 100.0, places=2)
        self.assertAlmostEqual(summary_row.debit, 50.0, places=2)
        self.assertAlmostEqual(summary_row.credit, 30.0, places=2)
        self.assertAlmostEqual(summary_row.total, 120.0, places=2)

        partner_1_row = rows.filtered(lambda r: r.code_account == self.account_receivable.code and r.third_party and r.vat_partner == "P1-0001")
        self.assertEqual(len(partner_1_row), 1)
        self.assertAlmostEqual(partner_1_row.inicial_amount, 100.0, places=2)
        self.assertAlmostEqual(partner_1_row.debit, 50.0, places=2)
        self.assertAlmostEqual(partner_1_row.credit, 0.0, places=2)
        self.assertAlmostEqual(partner_1_row.total, 150.0, places=2)

        partner_2_row = rows.filtered(lambda r: r.code_account == self.account_receivable.code and r.third_party and r.vat_partner == "P2-0001")
        self.assertEqual(len(partner_2_row), 1)
        self.assertAlmostEqual(partner_2_row.inicial_amount, 0.0, places=2)
        self.assertAlmostEqual(partner_2_row.debit, 0.0, places=2)
        self.assertAlmostEqual(partner_2_row.credit, 30.0, places=2)
        self.assertAlmostEqual(partner_2_row.total, -30.0, places=2)

    def test_partner_balance_does_not_carry_previous_year_on_expense(self):
        rows = self._run_partner_report(self.account_expense)
        summary_row = rows.filtered(lambda r: r.code_account == self.account_expense.code and not r.third_party)
        self.assertEqual(len(summary_row), 1)
        self.assertAlmostEqual(summary_row.inicial_amount, 0.0, places=2)
        self.assertAlmostEqual(summary_row.debit, 20.0, places=2)
        self.assertAlmostEqual(summary_row.credit, 0.0, places=2)
        self.assertAlmostEqual(summary_row.total, 20.0, places=2)

    def test_partner_filter_applies_to_summary_and_detail(self):
        rows = self._run_partner_report(self.account_receivable, self.partner_1)
        summary_row = rows.filtered(lambda r: r.code_account == self.account_receivable.code and not r.third_party)
        self.assertEqual(len(summary_row), 1)
        self.assertAlmostEqual(summary_row.inicial_amount, 100.0, places=2)
        self.assertAlmostEqual(summary_row.debit, 50.0, places=2)
        self.assertAlmostEqual(summary_row.credit, 0.0, places=2)
        self.assertAlmostEqual(summary_row.total, 150.0, places=2)

        partner_rows = rows.filtered(lambda r: r.code_account == self.account_receivable.code and r.third_party)
        self.assertEqual(len(partner_rows), 1)
        self.assertEqual(partner_rows.vat_partner, "P1-0001")

    def test_partner_summary_matches_general_totals(self):
        accounts = self.account_receivable | self.account_expense
        general_rows = self._run_general_report(accounts)
        partner_rows = self._run_partner_report(accounts)

        partner_summary = partner_rows.filtered(lambda r: not r.third_party)
        self.assertEqual(len(general_rows), len(partner_summary))

        for general_row in general_rows:
            matched_partner = partner_summary.filtered(lambda r: r.code_account == general_row.code_account)
            self.assertEqual(len(matched_partner), 1)
            self.assertAlmostEqual(matched_partner.inicial_amount, general_row.inicial_amount, places=2)
            self.assertAlmostEqual(matched_partner.debit, general_row.debit, places=2)
            self.assertAlmostEqual(matched_partner.credit, general_row.credit, places=2)
            self.assertAlmostEqual(matched_partner.total, general_row.total, places=2)
