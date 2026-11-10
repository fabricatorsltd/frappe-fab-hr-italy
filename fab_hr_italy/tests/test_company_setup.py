from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.exceptions import ValidationError

from fab_hr_italy.company_setup import (
	build_missing_company_cost_setup_updates,
	format_history_range,
	get_company_cost_history_suggestion,
	get_trailing_cost_months,
	provision_company_cost_setup,
	validate_company_cost_setup,
)


def raise_validation_error(message):
	raise ValidationError(str(message))


def build_company(**overrides):
	defaults = {
		"name": "Fabricators",
		"fab_hri_post_company_cost_to_payroll_entry": 1,
		"default_payroll_payable_account": "Payroll Payable - FAB",
		"fab_hri_gross_pay_expense_account": "",
		"fab_hri_employer_contribution_expense_account": "",
		"fab_hri_employer_contribution_payable_account": "",
		"fab_hri_employer_insurance_expense_account": "",
		"fab_hri_employer_insurance_payable_account": "",
		"fab_hri_tfr_expense_account": "",
		"fab_hri_tfr_payable_account": "",
	}
	defaults.update(overrides)
	return SimpleNamespace(**defaults)


class TestCompanySetup(unittest.TestCase):
	def test_build_missing_company_cost_setup_updates_creates_defaults(self):
		company = build_company()

		with (
			patch(
				"fab_hr_italy.company_setup.ensure_default_expense_account",
				side_effect=[
					"Salari e stipendi - FAB",
					"Contributi datore di lavoro - FAB",
					"Premi assicurativi INAIL - FAB",
					"Accantonamento TFR - FAB",
				],
			),
			patch(
				"fab_hr_italy.company_setup.ensure_default_liability_account",
				side_effect=[
					"Debiti v/INPS - FAB",
					"Debiti v/INAIL - FAB",
					"Fondo TFR - FAB",
				],
			),
		):
			updates = build_missing_company_cost_setup_updates(company)

		self.assertEqual(updates["fab_hri_gross_pay_expense_account"], "Salari e stipendi - FAB")
		self.assertEqual(updates["fab_hri_employer_contribution_expense_account"], "Contributi datore di lavoro - FAB")
		self.assertEqual(updates["fab_hri_employer_contribution_payable_account"], "Debiti v/INPS - FAB")
		self.assertEqual(updates["fab_hri_employer_insurance_expense_account"], "Premi assicurativi INAIL - FAB")
		self.assertEqual(updates["fab_hri_employer_insurance_payable_account"], "Debiti v/INAIL - FAB")
		self.assertEqual(updates["fab_hri_tfr_expense_account"], "Accantonamento TFR - FAB")
		self.assertEqual(updates["fab_hri_tfr_payable_account"], "Fondo TFR - FAB")

	def test_provision_company_cost_setup_updates_company(self):
		document = build_company()
		frappe_stub = SimpleNamespace(
			get_doc=Mock(return_value=document),
			db=SimpleNamespace(set_value=Mock()),
		)

		with (
			patch("fab_hr_italy.company_setup.frappe", new=frappe_stub),
			patch("fab_hr_italy.company_setup.normalize_company_cost_payable_accounts"),
			patch(
				"fab_hr_italy.company_setup.build_missing_company_cost_setup_updates",
				return_value={"fab_hri_tfr_payable_account": "Fondo TFR - FAB"},
			),
		):
			result = provision_company_cost_setup("Fabricators")

		self.assertEqual(result["company"], "Fabricators")
		self.assertEqual(result["updates"]["fab_hri_tfr_payable_account"], "Fondo TFR - FAB")
		frappe_stub.db.set_value.assert_called_once_with(
			"Company",
			"Fabricators",
			{"fab_hri_tfr_payable_account": "Fondo TFR - FAB"},
			update_modified=False,
		)

	def test_validate_company_cost_setup_requires_accounts_when_posting_enabled(self):
		document = build_company()

		with (
			patch("fab_hr_italy.company_setup.frappe.throw", side_effect=raise_validation_error),
			self.assertRaisesRegex(ValidationError, "Italy HR accounts"),
		):
			validate_company_cost_setup(document)

	def test_validate_company_cost_setup_allows_missing_accounts_when_posting_disabled(self):
		document = build_company(fab_hri_post_company_cost_to_payroll_entry=0)

		with patch("fab_hr_italy.company_setup.frappe.throw", side_effect=raise_validation_error):
			validate_company_cost_setup(document)

	def validate_contract_type_row(self, row, account):
		document = build_company(
			fab_hri_post_company_cost_to_payroll_entry=0,
			fab_hri_contract_type_accounts=[SimpleNamespace(contract_type="COLLABORATOR", **row)],
		)
		values = {"company": "Fabricators", "is_group": 0, "disabled": 0, "root_type": "Expense"}
		values.update(account)

		with (
			patch("fab_hr_italy.company_setup.frappe.get_cached_value", return_value=frappe._dict(values)),
			patch("fab_hr_italy.company_setup.frappe.throw", side_effect=raise_validation_error),
		):
			validate_company_cost_setup(document)

	def test_validate_company_cost_setup_accepts_a_contract_type_ledger_of_the_company(self):
		self.validate_contract_type_row({"gross_pay_expense_account": "Fees - TC"}, {})
		self.validate_contract_type_row(
			{"payroll_payable_account": "Fees Payable - TC"}, {"root_type": "Liability"}
		)

	def test_validate_company_cost_setup_refuses_an_unfit_contract_type_account(self):
		cases = (
			({"gross_pay_expense_account": "Fees - OTHER"}, {"company": "Other Company"}),
			({"gross_pay_expense_account": "Expenses - TC"}, {"is_group": 1}),
			({"gross_pay_expense_account": "Old Fees - TC"}, {"disabled": 1}),
			({"gross_pay_expense_account": "Payable - TC"}, {"root_type": "Liability"}),
			({"payroll_payable_account": "Fees - TC"}, {"root_type": "Expense"}),
		)
		for row, account in cases:
			with (
				self.subTest(row=row, account=account),
				self.assertRaisesRegex(ValidationError, "COLLABORATOR"),
			):
				self.validate_contract_type_row(row, account)

	def test_validate_company_cost_setup_refuses_a_repeated_contract_type(self):
		document = build_company(
			fab_hri_post_company_cost_to_payroll_entry=0,
			fab_hri_contract_type_accounts=[
				SimpleNamespace(contract_type="COLLABORATOR"),
				SimpleNamespace(contract_type="collaborator"),
			],
		)

		with (
			patch("fab_hr_italy.company_setup.frappe.throw", side_effect=raise_validation_error),
			self.assertRaisesRegex(ValidationError, "more than once"),
		):
			validate_company_cost_setup(document)

	def test_validate_company_cost_setup_requires_default_payroll_payable_account(self):
		document = build_company(
			fab_hri_gross_pay_expense_account="Salari e stipendi - FAB",
			fab_hri_employer_contribution_expense_account="Contributi datore di lavoro - FAB",
			fab_hri_employer_contribution_payable_account="Debiti v/INPS - FAB",
			fab_hri_employer_insurance_expense_account="Premi assicurativi INAIL - FAB",
			fab_hri_employer_insurance_payable_account="Debiti v/INAIL - FAB",
			fab_hri_tfr_expense_account="Accantonamento TFR - FAB",
			fab_hri_tfr_payable_account="Fondo TFR - FAB",
			default_payroll_payable_account="",
		)

		with (
			patch("fab_hr_italy.company_setup.validate_account_companies"),
			patch("fab_hr_italy.company_setup.frappe.throw", side_effect=raise_validation_error),
			self.assertRaisesRegex(ValidationError, "Default Payroll Payable Account"),
		):
			validate_company_cost_setup(document)

	def test_get_trailing_cost_months_limits_to_latest_distinct_months(self):
		months = get_trailing_cost_months(
			[
				{"cost_month": "2025-12-01"},
				{"cost_month": "2025-12-15"},
				{"cost_month": "2025-11-01"},
				{"cost_month": "2025-10-01"},
			],
			2,
		)

		self.assertEqual(months, {"2025-12-01", "2025-11-01"})

	def test_format_history_range_uses_month_labels(self):
		self.assertEqual(format_history_range("2025-10-01", "2025-12-01"), "10-2025 to 12-2025")
		self.assertEqual(format_history_range("2025-10-01", "2025-10-01"), "10-2025")

	def test_get_company_cost_history_suggestion_returns_config_updates(self):
		with patch(
			"fab_hr_italy.company_setup.get_company_employee_cost_rows",
			return_value=[{"cost_month": "2025-10-01"}],
		), patch(
			"fab_hr_italy.company_setup.summarize_employee_cost_history",
		), patch(
			"fab_hr_italy.company_setup.serialize_employee_cost_history_summary",
			return_value={
				"basis_mode": "Gross Pay",
				"from_month": "2025-10-01",
				"to_month": "2025-12-01",
				"employer_contribution_rate": 30.0,
				"employer_insurance_rate": 1.0,
				"tfr_rate": 7.41,
			},
		):
			suggestion = get_company_cost_history_suggestion("Fabricators", 3)

		self.assertEqual(suggestion["config_updates"]["fab_hri_enabled"], 1)
		self.assertEqual(suggestion["config_updates"]["fab_hri_costing_basis"], "Gross Pay")
		self.assertEqual(suggestion["config_updates"]["fab_hri_employer_contribution_rate"], 30.0)
		self.assertEqual(suggestion["history_range_label"], "10-2025 to 12-2025")
