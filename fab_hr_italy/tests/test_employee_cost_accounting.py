from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fab_hr_italy.company_costing import CompanyCostConfig
from fab_hr_italy.employee_cost_accounting import (
	build_employee_cost_accrual_accounts,
	cleanup_failed_employee_cost_accrual_journal_entry,
	create_employee_cost_accrual_journal_entry,
)


class TestEmployeeCostAccounting(unittest.TestCase):
	def test_build_employee_cost_accrual_accounts_aggregates_month_amounts(self):
		config = CompanyCostConfig(
			enabled=True,
			post_to_payroll_entry=True,
			gross_pay_expense_account="Salari e stipendi - FAB",
			payroll_payable_account="Payroll Payable - FAB",
			employer_contribution_expense_account="Contributi datore di lavoro - FAB",
			employer_contribution_payable_account="Debiti v/INPS - FAB",
			employer_insurance_expense_account="Premi assicurativi INAIL - FAB",
			employer_insurance_payable_account="Debiti v/INAIL - FAB",
			tfr_expense_account="Accantonamento TFR - FAB",
			tfr_payable_account="Fondo TFR - FAB",
		)

		rows = [
			{
				"gross_monthly_amount": 1000,
				"employer_contribution_amount": 300,
				"inail_amount": 10,
				"tfr_accrual_amount": 74.1,
				"indirect_cost_accrued_amount": 274.1,
				"indirect_cost_paid_amount": 30,
			},
			{
				"gross_monthly_amount": 500,
				"employer_contribution_amount": 150,
				"inail_amount": 5,
				"tfr_accrual_amount": 37.05,
			},
		]

		account_rows = build_employee_cost_accrual_accounts(rows, config, "Main - FAB")
		lookup = {(row["account"], row["debit_in_account_currency"] > 0): row for row in account_rows}

		self.assertEqual(lookup[("Salari e stipendi - FAB", True)]["debit_in_account_currency"], 1670.0)
		self.assertEqual(lookup[("Payroll Payable - FAB", False)]["credit_in_account_currency"], 1670.0)
		self.assertEqual(
			lookup[("Contributi datore di lavoro - FAB", True)]["debit_in_account_currency"], 450.0
		)
		self.assertEqual(lookup[("Debiti v/INPS - FAB", False)]["credit_in_account_currency"], 450.0)
		self.assertEqual(lookup[("Premi assicurativi INAIL - FAB", True)]["debit_in_account_currency"], 15.0)
		self.assertEqual(lookup[("Debiti v/INAIL - FAB", False)]["credit_in_account_currency"], 15.0)
		self.assertEqual(
			lookup[("Accantonamento TFR - FAB", True)]["debit_in_account_currency"], 111.15
		)
		self.assertEqual(lookup[("Fondo TFR - FAB", False)]["credit_in_account_currency"], 111.15)

	def test_build_employee_cost_accrual_accounts_keeps_cost_center(self):
		config = CompanyCostConfig(
			enabled=True,
			post_to_payroll_entry=True,
			gross_pay_expense_account="Salari e stipendi - FAB",
			payroll_payable_account="Payroll Payable - FAB",
		)

		account_rows = build_employee_cost_accrual_accounts(
			[{"gross_monthly_amount": 1000}],
			config,
			"Main - FAB",
		)

		self.assertTrue(account_rows)
		self.assertTrue(all(row["cost_center"] == "Main - FAB" for row in account_rows))

	def test_build_employee_cost_accrual_accounts_splits_lines_by_contract_type(self):
		config = make_full_cost_config()
		rows = [
			{
				"contract_type": "EMPLOYEE",
				"gross_monthly_amount": 1000,
				"employer_contribution_amount": 300,
				"inail_amount": 10,
				"tfr_accrual_amount": 74.1,
			},
			{
				"contract_type": "COLLABORATOR",
				"gross_monthly_amount": 2000,
				"employer_contribution_amount": 480,
			},
			{
				"contract_type": " collaborator ",
				"gross_monthly_amount": 500,
				"employer_contribution_amount": 120,
			},
		]
		overrides = {
			"COLLABORATOR": {
				"gross_pay_expense_account": "Collaborator Fees - TC",
				"employer_contribution_expense_account": "Collaborator Contributions - TC",
				"employer_contribution_payable_account": "Collaborator Contributions Payable - TC",
			}
		}

		account_rows = build_employee_cost_accrual_accounts(rows, config, "Main - TC", overrides)
		lookup = {(row["account"], row["debit_in_account_currency"] > 0): row for row in account_rows}

		self.assertEqual(lookup[("Gross Pay - TC", True)]["debit_in_account_currency"], 1000.0)
		self.assertEqual(lookup[("Collaborator Fees - TC", True)]["debit_in_account_currency"], 2500.0)
		# no payable override: both contract types credit the same payroll payable line
		self.assertEqual(lookup[("Payroll Payable - TC", False)]["credit_in_account_currency"], 3500.0)
		self.assertEqual(lookup[("Contributions - TC", True)]["debit_in_account_currency"], 300.0)
		self.assertEqual(lookup[("Contributions Payable - TC", False)]["credit_in_account_currency"], 300.0)
		self.assertEqual(
			lookup[("Collaborator Contributions - TC", True)]["debit_in_account_currency"], 600.0
		)
		self.assertEqual(
			lookup[("Collaborator Contributions Payable - TC", False)]["credit_in_account_currency"], 600.0
		)
		self.assertEqual(lookup[("TFR - TC", True)]["debit_in_account_currency"], 74.1)
		self.assertEqual(len(account_rows), 11)
		self.assertEqual(
			sum(row["debit_in_account_currency"] for row in account_rows),
			sum(row["credit_in_account_currency"] for row in account_rows),
		)

	def test_build_employee_cost_accrual_accounts_without_override_is_unchanged(self):
		config = make_full_cost_config()
		rows = [
			{
				"contract_type": "EMPLOYEE",
				"gross_monthly_amount": 1000.005,
				"employer_contribution_amount": 300,
				"inail_amount": 10,
				"tfr_accrual_amount": 74.1,
			},
			{
				"contract_type": "COLLABORATOR",
				"gross_monthly_amount": 2000.004,
				"employer_contribution_amount": 480,
				"indirect_cost_accrued_amount": 100,
				"indirect_cost_paid_amount": 20,
			},
		]
		expected = [
			{
				"account": "Gross Pay - TC",
				"debit_in_account_currency": 3080.01,
				"credit_in_account_currency": 0.0,
				"cost_center": "Main - TC",
			},
			{
				"account": "Payroll Payable - TC",
				"debit_in_account_currency": 0.0,
				"credit_in_account_currency": 3080.01,
				"cost_center": "Main - TC",
			},
			{
				"account": "Contributions - TC",
				"debit_in_account_currency": 780.0,
				"credit_in_account_currency": 0.0,
				"cost_center": "Main - TC",
			},
			{
				"account": "Contributions Payable - TC",
				"debit_in_account_currency": 0.0,
				"credit_in_account_currency": 780.0,
				"cost_center": "Main - TC",
			},
			{
				"account": "Insurance - TC",
				"debit_in_account_currency": 10.0,
				"credit_in_account_currency": 0.0,
				"cost_center": "Main - TC",
			},
			{
				"account": "Insurance Payable - TC",
				"debit_in_account_currency": 0.0,
				"credit_in_account_currency": 10.0,
				"cost_center": "Main - TC",
			},
			{
				"account": "TFR - TC",
				"debit_in_account_currency": 74.1,
				"credit_in_account_currency": 0.0,
				"cost_center": "Main - TC",
			},
			{
				"account": "TFR Payable - TC",
				"debit_in_account_currency": 0.0,
				"credit_in_account_currency": 74.1,
				"cost_center": "Main - TC",
			},
		]

		self.assertEqual(build_employee_cost_accrual_accounts(rows, config, "Main - TC"), expected)
		# an override for a contract type the month does not carry changes nothing
		self.assertEqual(
			build_employee_cost_accrual_accounts(
				rows, config, "Main - TC", {"INTERN": {"gross_pay_expense_account": "Intern Fees - TC"}}
			),
			expected,
		)

	def test_create_employee_cost_accrual_journal_entry_marks_party_not_required(self):
		journal_entry = SimpleNamespace(insert=Mock(), submit=Mock(), name="ACC-JV-2026-00001")
		frappe_stub = SimpleNamespace(
			get_doc=Mock(return_value=journal_entry),
			get_cached_value=Mock(return_value="EUR"),
		)

		with patch("fab_hr_italy.employee_cost_accounting.frappe", new=frappe_stub):
			result = create_employee_cost_accrual_journal_entry(
				company="fabricators",
				cost_month="2025-12-01",
				currency="EUR",
				accounts=[{"account": "Salari e stipendi - FAB", "debit_in_account_currency": 1000.0}],
			)

		payload = frappe_stub.get_doc.call_args.args[0]
		self.assertEqual(payload["party_not_required"], 1)
		self.assertEqual(result, journal_entry)
		journal_entry.insert.assert_called_once_with(ignore_permissions=True)
		journal_entry.submit.assert_called_once_with()

	def test_create_employee_cost_accrual_journal_entry_cleans_up_failed_submit_without_gl(self):
		journal_entry = SimpleNamespace(
			insert=Mock(),
			submit=Mock(side_effect=RuntimeError("submit failed")),
			name="ACC-JV-2026-00004",
		)
		frappe_stub = SimpleNamespace(
			get_doc=Mock(return_value=journal_entry),
			get_cached_value=Mock(return_value="EUR"),
			db=SimpleNamespace(
				exists=Mock(side_effect=lambda doctype, name: True if doctype == "Journal Entry" else False),
				get_value=Mock(return_value=1),
				set_value=Mock(),
			),
			delete_doc=Mock(),
		)

		with (
			patch("fab_hr_italy.employee_cost_accounting.frappe", new=frappe_stub),
			self.assertRaisesRegex(RuntimeError, "submit failed"),
		):
			create_employee_cost_accrual_journal_entry(
				company="fabricators",
				cost_month="2025-12-01",
				currency="EUR",
				accounts=[{"account": "Salari e stipendi - FAB", "debit_in_account_currency": 1000.0}],
			)

		frappe_stub.db.set_value.assert_called_once_with(
			"Journal Entry", "ACC-JV-2026-00004", "docstatus", 0, update_modified=False
		)
		frappe_stub.delete_doc.assert_called_once_with(
			"Journal Entry", "ACC-JV-2026-00004", ignore_permissions=True, force=1
		)

	def test_cleanup_failed_employee_cost_accrual_journal_entry_cancels_when_gl_exists(self):
		journal_entry = SimpleNamespace(cancel=Mock())
		frappe_stub = SimpleNamespace(
			db=SimpleNamespace(
				exists=Mock(
					side_effect=lambda doctype, name: True
					if doctype == "Journal Entry"
					else {"voucher_type": "Journal Entry", "voucher_no": "ACC-JV-2026-00005", "is_cancelled": 0}
				),
				get_value=Mock(return_value=1),
				set_value=Mock(),
			),
			get_doc=Mock(return_value=journal_entry),
			delete_doc=Mock(),
		)

		with patch("fab_hr_italy.employee_cost_accounting.frappe", new=frappe_stub):
			cleanup_failed_employee_cost_accrual_journal_entry("ACC-JV-2026-00005")

		journal_entry.cancel.assert_called_once_with()
		frappe_stub.delete_doc.assert_not_called()


def make_full_cost_config() -> CompanyCostConfig:
	return CompanyCostConfig(
		enabled=True,
		post_to_payroll_entry=True,
		gross_pay_expense_account="Gross Pay - TC",
		payroll_payable_account="Payroll Payable - TC",
		employer_contribution_expense_account="Contributions - TC",
		employer_contribution_payable_account="Contributions Payable - TC",
		employer_insurance_expense_account="Insurance - TC",
		employer_insurance_payable_account="Insurance Payable - TC",
		tfr_expense_account="TFR - TC",
		tfr_payable_account="TFR Payable - TC",
	)
