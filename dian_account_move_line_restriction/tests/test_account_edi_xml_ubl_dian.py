from copy import deepcopy

from odoo.addons.dian_account_move_line_restriction.models.account_edi_xml_ubl_dian import (
    AccountEdiXmlUBLDian,
)
from odoo.tests.common import BaseCase


class _GroupingHelper:
    _line_group_key = AccountEdiXmlUBLDian._line_group_key
    _tax_subtotal_signature = AccountEdiXmlUBLDian._tax_subtotal_signature
    _recompute_tax_subtotal_amount = AccountEdiXmlUBLDian._recompute_tax_subtotal_amount
    _recompute_document_tax_totals = AccountEdiXmlUBLDian._recompute_document_tax_totals
    _merge_tax_subtotal_vals = AccountEdiXmlUBLDian._merge_tax_subtotal_vals
    _merge_tax_total_vals = AccountEdiXmlUBLDian._merge_tax_total_vals
    _allowance_signature = AccountEdiXmlUBLDian._allowance_signature
    _merge_allowance_charge_vals = AccountEdiXmlUBLDian._merge_allowance_charge_vals
    _merge_price_vals = AccountEdiXmlUBLDian._merge_price_vals
    _merge_grouped_line_vals = AccountEdiXmlUBLDian._merge_grouped_line_vals


class TestAccountEdiXmlUblDianGrouping(BaseCase):
    def setUp(self):
        super().setUp()
        self.edi_builder = _GroupingHelper()

    def _make_line_vals(
        self, *, quantity, extension, tax_amount, taxable_amount, unit_price, discount_amount
    ):
        return {
            "line_quantity": quantity,
            "line_extension_amount": extension,
            "tax_total_vals": [
                {
                    "tax_co_type": "01",
                    "tax_amount": tax_amount,
                    "tax_subtotal_vals": [
                        {
                            "tax_amount": tax_amount,
                            "taxable_amount": taxable_amount,
                            "tax_category_vals": {
                                "percent": "19.00",
                                "tax_scheme_vals": {"id": "01", "name": "IVA"},
                            },
                        }
                    ],
                }
            ],
            "withholding_tax_total_vals_list": [
                {
                    "tax_co_type": "06",
                    "tax_amount": tax_amount / 10.0,
                    "tax_subtotal_vals": [
                        {
                            "tax_amount": tax_amount / 10.0,
                            "taxable_amount": taxable_amount,
                            "tax_category_vals": {
                                "percent": "1.00",
                                "tax_scheme_vals": {"id": "06", "name": "ReteRenta"},
                            },
                        }
                    ],
                }
            ],
            "allowance_charge_vals": [
                {
                    "charge_indicator": "false",
                    "allowance_charge_reason_code": "00",
                    "multiplier_factor": 10.0,
                    "amount": discount_amount,
                    "base_amount": taxable_amount + discount_amount,
                }
            ],
            "price_vals": {
                "price_amount": unit_price,
                "base_quantity": quantity,
                "base_quantity_attrs": {"unitCode": "EA"},
            },
        }

    def test_merge_grouped_line_vals_sums_base_and_taxes_without_duplication(self):
        grouped_line = self._make_line_vals(
            quantity=2.0,
            extension=200.0,
            tax_amount=38.0,
            taxable_amount=200.0,
            unit_price=100.0,
            discount_amount=20.0,
        )
        incoming_line = self._make_line_vals(
            quantity=3.0,
            extension=300.0,
            tax_amount=57.0,
            taxable_amount=300.0,
            unit_price=120.0,
            discount_amount=30.0,
        )

        self.edi_builder._merge_grouped_line_vals(grouped_line, incoming_line, 0.01)

        self.assertEqual(grouped_line["line_quantity"], 5.0)
        self.assertEqual(grouped_line["line_extension_amount"], 500.0)
        self.assertEqual(grouped_line["tax_total_vals"][0]["tax_amount"], 95.0)
        self.assertEqual(grouped_line["tax_total_vals"][0]["tax_subtotal_vals"][0]["tax_amount"], 95.0)
        self.assertEqual(
            grouped_line["tax_total_vals"][0]["tax_subtotal_vals"][0]["taxable_amount"], 500.0
        )
        self.assertEqual(grouped_line["withholding_tax_total_vals_list"][0]["tax_amount"], 5.0)
        self.assertEqual(grouped_line["allowance_charge_vals"][0]["amount"], 50.0)
        self.assertEqual(grouped_line["allowance_charge_vals"][0]["base_amount"], 550.0)
        self.assertEqual(grouped_line["price_vals"]["base_quantity"], 5.0)
        self.assertAlmostEqual(grouped_line["price_vals"]["price_amount"], 112.0)

    def test_line_group_key_separates_different_discount(self):
        key_with_discount_0 = self.edi_builder._line_group_key(10, [1, 2], 0.0, 1)
        key_with_discount_5 = self.edi_builder._line_group_key(10, [1, 2], 5.0, 1)
        self.assertNotEqual(key_with_discount_0, key_with_discount_5)

    def test_line_group_key_separates_different_taxes(self):
        key_iva_19 = self.edi_builder._line_group_key(10, [1, 2], 0.0, 1)
        key_iva_5 = self.edi_builder._line_group_key(10, [1, 3], 0.0, 1)
        self.assertNotEqual(key_iva_19, key_iva_5)

    def test_merge_tax_totals_keeps_different_rates_in_separate_subtotals(self):
        grouped_line = self._make_line_vals(
            quantity=1.0,
            extension=100.0,
            tax_amount=19.0,
            taxable_amount=100.0,
            unit_price=100.0,
            discount_amount=0.0,
        )
        incoming_line = deepcopy(grouped_line)
        incoming_line["tax_total_vals"][0]["tax_amount"] = 5.0
        incoming_line["tax_total_vals"][0]["tax_subtotal_vals"][0]["tax_amount"] = 5.0
        incoming_line["tax_total_vals"][0]["tax_subtotal_vals"][0]["taxable_amount"] = 100.0
        incoming_line["tax_total_vals"][0]["tax_subtotal_vals"][0]["tax_category_vals"]["percent"] = "5.00"

        self.edi_builder._merge_tax_total_vals(grouped_line, incoming_line, "tax_total_vals", 0.01)

        self.assertEqual(grouped_line["tax_total_vals"][0]["tax_amount"], 24.0)
        self.assertEqual(len(grouped_line["tax_total_vals"][0]["tax_subtotal_vals"]), 2)

    def test_recompute_document_withholding_tax_total_from_base_and_percent(self):
        vals = {
            "withholding_tax_total_vals": [
                {
                    "tax_amount": 1669461.53,
                    "tax_subtotal_vals": [
                        {
                            "taxable_amount": 66778362.00,
                            "tax_amount": 1669461.53,
                            "tax_category_vals": {
                                "percent": "2.50",
                                "tax_scheme_vals": {"id": "06", "name": "ReteRenta"},
                            },
                        }
                    ],
                }
            ],
        }
        self.edi_builder._recompute_document_tax_totals(vals, 0.01)
        self.assertEqual(vals["withholding_tax_total_vals"][0]["tax_amount"], 1669459.05)
