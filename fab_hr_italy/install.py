from __future__ import annotations

from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	ensure_custom_fields()
	sync_fab_group()


def after_migrate():
	ensure_custom_fields()
	sync_fab_group()


def ensure_custom_fields():
	create_custom_fields(get_custom_fields(), update=True)


def get_custom_fields() -> dict[str, list[dict[str, object]]]:
	return {
		"Company": [
			{
				"fieldname": "fab_hri_section",
				"label": _("Italy HR Payroll"),
				"fieldtype": "Section Break",
				"insert_after": "default_payroll_payable_account",
			},
			{
				"fieldname": "fab_hri_enabled",
				"label": _("Enable Italy HR Payroll"),
				"fieldtype": "Check",
				"insert_after": "fab_hri_section",
			},
			{
				"fieldname": "fab_hri_costing_basis",
				"label": _("Company Cost Basis"),
				"fieldtype": "Select",
				"options": "\nGross Pay",
				"default": "Gross Pay",
				"insert_after": "fab_hri_enabled",
			},
			{
				"fieldname": "fab_hri_employer_contribution_rate",
				"label": _("Employer Contribution Rate"),
				"fieldtype": "Percent",
				"insert_after": "fab_hri_costing_basis",
			},
			{
				"fieldname": "fab_hri_employer_insurance_rate",
				"label": _("Employer Insurance Rate"),
				"fieldtype": "Percent",
				"insert_after": "fab_hri_employer_contribution_rate",
			},
			{
				"fieldname": "fab_hri_tfr_rate",
				"label": _("TFR Accrual Rate"),
				"fieldtype": "Percent",
				"default": "7.41",
				"insert_after": "fab_hri_employer_insurance_rate",
			},
			{
				"fieldname": "fab_hri_column_break",
				"fieldtype": "Column Break",
				"insert_after": "fab_hri_tfr_rate",
			},
			{
				"fieldname": "fab_hri_post_company_cost_to_payroll_entry",
				"label": _("Post Company Cost In Payroll Accrual Entry"),
				"fieldtype": "Check",
				"insert_after": "fab_hri_column_break",
			},
			{
				"fieldname": "fab_hri_accounts_section",
				"label": _("Italy HR Payroll Accounts"),
				"fieldtype": "Section Break",
				"insert_after": "fab_hri_post_company_cost_to_payroll_entry",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_gross_pay_expense_account",
				"label": _("Gross Pay Expense Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_accounts_section",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_employer_contribution_expense_account",
				"label": _("Employer Contribution Expense Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_gross_pay_expense_account",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_employer_contribution_payable_account",
				"label": _("Employer Contribution Payable Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_employer_contribution_expense_account",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_accounts_column_break",
				"fieldtype": "Column Break",
				"insert_after": "fab_hri_employer_contribution_payable_account",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_employer_insurance_expense_account",
				"label": _("Employer Insurance Expense Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_accounts_column_break",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_employer_insurance_payable_account",
				"label": _("Employer Insurance Payable Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_employer_insurance_expense_account",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_tfr_expense_account",
				"label": _("TFR Expense Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_employer_insurance_payable_account",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
			{
				"fieldname": "fab_hri_tfr_payable_account",
				"label": _("TFR Payable Account"),
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": "fab_hri_tfr_expense_account",
				"depends_on": "eval:doc.fab_hri_post_company_cost_to_payroll_entry",
			},
		],
		"Employee": [
			{
				"fieldname": "fab_hri_employee_section",
				"label": _("Italy HR Payroll Overrides"),
				"fieldtype": "Section Break",
				"insert_after": "ctc",
			},
			{
				"fieldname": "fab_hri_apply_employee_overrides",
				"label": _("Apply Employee-Specific Italy HR Rates"),
				"fieldtype": "Check",
				"insert_after": "fab_hri_employee_section",
			},
			{
				"fieldname": "fab_hri_employer_contribution_rate_override",
				"label": _("Employer Contribution Rate Override"),
				"fieldtype": "Percent",
				"insert_after": "fab_hri_apply_employee_overrides",
				"depends_on": "eval:doc.fab_hri_apply_employee_overrides",
			},
			{
				"fieldname": "fab_hri_employer_insurance_rate_override",
				"label": _("Employer Insurance Rate Override"),
				"fieldtype": "Percent",
				"insert_after": "fab_hri_employer_contribution_rate_override",
				"depends_on": "eval:doc.fab_hri_apply_employee_overrides",
			},
			{
				"fieldname": "fab_hri_employee_column_break",
				"fieldtype": "Column Break",
				"insert_after": "fab_hri_employer_insurance_rate_override",
				"depends_on": "eval:doc.fab_hri_apply_employee_overrides",
			},
			{
				"fieldname": "fab_hri_tfr_rate_override",
				"label": _("TFR Accrual Rate Override"),
				"fieldtype": "Percent",
				"insert_after": "fab_hri_employee_column_break",
				"depends_on": "eval:doc.fab_hri_apply_employee_overrides",
			},
		],
		"Salary Slip": [
			{
				"fieldname": "fab_hri_costing_section",
				"label": _("Italy Company Cost"),
				"fieldtype": "Section Break",
				"insert_after": "journal_entry",
			},
			{
				"fieldname": "fab_hri_costing_basis_amount",
				"label": _("Company Cost Basis Amount"),
				"fieldtype": "Currency",
				"read_only": 1,
				"insert_after": "fab_hri_costing_section",
			},
			{
				"fieldname": "fab_hri_employer_contribution_amount",
				"label": _("Employer Contribution Amount"),
				"fieldtype": "Currency",
				"read_only": 1,
				"insert_after": "fab_hri_costing_basis_amount",
			},
			{
				"fieldname": "fab_hri_employer_insurance_amount",
				"label": _("Employer Insurance Amount"),
				"fieldtype": "Currency",
				"read_only": 1,
				"insert_after": "fab_hri_employer_contribution_amount",
			},
			{
				"fieldname": "fab_hri_tfr_accrual_amount",
				"label": _("TFR Accrual Amount"),
				"fieldtype": "Currency",
				"read_only": 1,
				"insert_after": "fab_hri_employer_insurance_amount",
			},
			{
				"fieldname": "fab_hri_total_company_cost",
				"label": _("Total Company Cost"),
				"fieldtype": "Currency",
				"read_only": 1,
				"insert_after": "fab_hri_tfr_accrual_amount",
			},
		],
	}


def sync_fab_group():
	from fab.install import sync_fab_desktop_group

	sync_fab_desktop_group()
