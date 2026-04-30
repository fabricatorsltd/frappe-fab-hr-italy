from __future__ import annotations

import frappe
from frappe import _

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry as HRMSPayrollEntry

from fab_hr_italy.company_costing import get_company_cost_config


class PayrollEntry(HRMSPayrollEntry):
	def make_accrual_jv_entry(self, submitted_salary_slips):
		self.check_permission("write")
		employee_wise_accounting_enabled = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)
		self.employee_based_payroll_payable_entries = {}
		self._advance_deduction_entries = []

		earnings = (
			self.get_salary_component_total(
				component_type="earnings",
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)
			or {}
		)

		deductions = (
			self.get_salary_component_total(
				component_type="deductions",
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)
			or {}
		)

		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		if earnings or deductions:
			accounts = []
			currencies = []
			payable_amount = 0
			accounting_dimensions = get_accounting_dimensions() or []
			company_currency = erpnext.get_company_currency(self.company)

			payable_amount = self.get_payable_amount_for_earnings_and_deductions(
				accounts,
				earnings,
				deductions,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
				employee_wise_accounting_enabled,
			)

			payable_amount = self.set_accounting_entries_for_advance_deductions(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
			)

			payable_amount = self.add_italian_company_cost_entries(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
			)

			self.set_payable_amount_against_payroll_payable_account(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
				self.payroll_payable_account,
				employee_wise_accounting_enabled,
			)

			self.make_journal_entry(
				accounts,
				currencies,
				self.payroll_payable_account,
				voucher_type="Journal Entry",
				user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
					self.start_date, self.end_date
				),
				submit_journal_entry=True,
				submitted_salary_slips=submitted_salary_slips,
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)

	def add_italian_company_cost_entries(
		self,
		accounts,
		currencies,
		company_currency,
		accounting_dimensions,
		precision,
		payable_amount,
	):
		config = get_company_cost_config(self.company)
		if not (config.enabled and config.post_to_payroll_entry):
			return payable_amount

		salary_slip_rows = self.get_italian_company_cost_rows()
		if not salary_slip_rows:
			return payable_amount

		account_pairs = [
			(
				"fab_hri_employer_contribution_amount",
				config.employer_contribution_expense_account,
				config.employer_contribution_payable_account,
				_("Employer contribution"),
			),
			(
				"fab_hri_employer_insurance_amount",
				config.employer_insurance_expense_account,
				config.employer_insurance_payable_account,
				_("Employer insurance"),
			),
			(
				"fab_hri_tfr_accrual_amount",
				config.tfr_expense_account,
				config.tfr_payable_account,
				_("TFR accrual"),
			),
		]

		for fieldname, expense_account, payable_account, label in account_pairs:
			total_amount = sum((row.get(fieldname) or 0) for row in salary_slip_rows)
			if not total_amount:
				continue

			if not expense_account or not payable_account:
				frappe.throw(
					_(
						"Missing Italy HR account configuration for {0} on Company {1}"
					).format(label, self.company)
				)

			for row in salary_slip_rows:
				amount = row.get(fieldname) or 0
				if not amount:
					continue

				cost_centers = self.get_payroll_cost_centers_for_employee(
					row.employee,
					row.salary_structure,
				)
				for cost_center, percentage in cost_centers.items():
					amount_against_cost_center = amount * percentage / 100
					payable_amount = self.get_accounting_entries_and_payable_amount(
						expense_account,
						cost_center or self.cost_center,
						amount_against_cost_center,
						currencies,
						company_currency,
						payable_amount,
						accounting_dimensions,
						precision,
						entry_type="debit",
						accounts=accounts,
					)
					payable_amount = self.get_accounting_entries_and_payable_amount(
						payable_account,
						cost_center or self.cost_center,
						amount_against_cost_center,
						currencies,
						company_currency,
						payable_amount,
						accounting_dimensions,
						precision,
						entry_type="credit",
						accounts=accounts,
					)

		return payable_amount

	def get_italian_company_cost_rows(self):
		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)
		if not salary_slips:
			return []

		SalarySlip = frappe.qb.DocType("Salary Slip")
		return (
			frappe.qb.from_(SalarySlip)
			.select(
				SalarySlip.employee,
				SalarySlip.salary_structure,
				SalarySlip.fab_hri_employer_contribution_amount,
				SalarySlip.fab_hri_employer_insurance_amount,
				SalarySlip.fab_hri_tfr_accrual_amount,
			)
			.where(SalarySlip.name.isin([row.name for row in salary_slips]))
		).run(as_dict=True)