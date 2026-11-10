from __future__ import annotations

from typing import Any

import frappe
from erpnext.setup.setup_wizard.operations.taxes_setup import get_or_create_account
from frappe import _
from frappe.utils import cint, cstr, formatdate, get_first_day, getdate

from fab_hr_italy.company_costing import (
	build_employee_cost_forecast,
	serialize_employee_cost_history_summary,
	summarize_employee_cost_history,
)

HR_ACCOUNT_FIELDS = {
	"fab_hri_gross_pay_expense_account": {
		"label": _("Gross Pay Expense Account"),
		"account_name": "Salari e stipendi",
		"root_type": "Expense",
	},
	"fab_hri_employer_contribution_expense_account": {
		"label": _("Employer Contribution Expense Account"),
		"account_name": "Contributi datore di lavoro",
		"root_type": "Expense",
	},
	"fab_hri_employer_contribution_payable_account": {
		"label": _("Employer Contribution Payable Account"),
		"account_name": "Debiti v/INPS",
		"root_type": "Liability",
	},
	"fab_hri_employer_insurance_expense_account": {
		"label": _("Employer Insurance Expense Account"),
		"account_name": "Premi assicurativi INAIL",
		"root_type": "Expense",
	},
	"fab_hri_employer_insurance_payable_account": {
		"label": _("Employer Insurance Payable Account"),
		"account_name": "Debiti v/INAIL",
		"root_type": "Liability",
	},
	"fab_hri_tfr_expense_account": {
		"label": _("TFR Expense Account"),
		"account_name": "Accantonamento TFR",
		"root_type": "Expense",
	},
	"fab_hri_tfr_payable_account": {
		"label": _("TFR Payable Account"),
		"account_name": "Fondo TFR",
		"root_type": "Liability",
	},
}

CONTRACT_TYPE_ACCOUNT_FIELDS = (
	"gross_pay_expense_account",
	"payroll_payable_account",
	"employer_contribution_expense_account",
	"employer_contribution_payable_account",
	"employer_insurance_expense_account",
	"employer_insurance_payable_account",
	"tfr_expense_account",
	"tfr_payable_account",
)

EMPLOYEE_COST_HISTORY_FIELDS = [
	"cost_month",
	"employee",
	"employee_name",
	"employee_identifier",
	"source_type",
	"gross_monthly_amount",
	"employer_contribution_amount",
	"inail_amount",
	"tfr_accrual_amount",
	"total_company_cost",
	"currency",
]


def validate_company_cost_setup(document: Any, method: str | None = None) -> None:
	company = cstr(get_document_value(document, "name")).strip()
	validate_account_companies(document, company)

	if not cint(get_document_value(document, "fab_hri_post_company_cost_to_payroll_entry")):
		return

	missing_labels = get_missing_company_cost_account_labels(document)
	if missing_labels:
		frappe.throw(
			_("Set the missing Italy HR accounts before enabling payroll-entry posting: {0}.").format(
				", ".join(missing_labels)
			)
		)

	if not cstr(get_document_value(document, "default_payroll_payable_account")).strip():
		frappe.throw(
			_("Set Default Payroll Payable Account before enabling payroll-entry posting.")
		)


@frappe.whitelist()
def provision_company_cost_setup(company: str) -> dict[str, Any]:
	document = frappe.get_doc("Company", company)
	updates = build_missing_company_cost_setup_updates(document)
	normalize_company_cost_payable_accounts(document)
	if not updates:
		return {
			"company": company,
			"updated_fields": [],
			"updates": {},
			"message": _("Italy HR payroll setup is already complete."),
		}

	frappe.db.set_value("Company", company, updates, update_modified=False)
	return {
		"company": company,
		"updated_fields": sorted(updates),
		"updates": updates,
		"message": _("Provisioned Italy HR payroll setup for {0}.").format(company),
	}


@frappe.whitelist()
def get_company_cost_history_suggestion(company: str, trailing_months: int = 6) -> dict[str, Any]:
	rows = get_company_employee_cost_rows(company, trailing_months)
	summary_doc = summarize_employee_cost_history(rows)
	summary = serialize_employee_cost_history_summary(summary_doc)
	return {
		"company": company,
		"history_range_label": format_history_range(summary["from_month"], summary["to_month"]),
		"config_updates": {
			"fab_hri_enabled": 1,
			"fab_hri_costing_basis": summary["basis_mode"],
			"fab_hri_employer_contribution_rate": summary["employer_contribution_rate"],
			"fab_hri_employer_insurance_rate": summary["employer_insurance_rate"],
			"fab_hri_tfr_rate": summary["tfr_rate"],
		},
		**summary,
	}


@frappe.whitelist()
def preview_employee_cost_forecast(
	company: str,
	trailing_months: int = 6,
	forecast_months: int = 3,
) -> dict[str, Any]:
	rows = get_company_employee_cost_rows(company, trailing_months)
	summary_doc = summarize_employee_cost_history(rows)
	summary = serialize_employee_cost_history_summary(summary_doc)
	forecast_months = cint(forecast_months)
	if forecast_months < 1:
		frappe.throw(_("Forecast Months must be at least 1."))

	return {
		"company": company,
		"history_range_label": format_history_range(summary["from_month"], summary["to_month"]),
		"forecast": build_employee_cost_forecast(summary_doc, forecast_months),
		**summary,
	}


def build_missing_company_cost_setup_updates(document: Any) -> dict[str, str]:
	company = cstr(get_document_value(document, "name")).strip()
	if not company:
		frappe.throw(_("Set Company before provisioning HR payroll setup."))

	updates: dict[str, str] = {}
	for fieldname, spec in HR_ACCOUNT_FIELDS.items():
		if cstr(get_document_value(document, fieldname)).strip():
			continue

		if spec["root_type"] == "Expense":
			updates[fieldname] = ensure_default_expense_account(company, spec["account_name"])
		else:
			updates[fieldname] = ensure_default_liability_account(company, spec["account_name"])

	return updates


def get_company_employee_cost_history_summary(company: str, trailing_months: int = 6) -> dict[str, Any]:
	rows = get_company_employee_cost_rows(company, trailing_months)
	summary = summarize_employee_cost_history(rows)
	return serialize_employee_cost_history_summary(summary)


def get_company_employee_cost_rows(company: str, trailing_months: int = 6) -> list[dict[str, Any]]:
	company = cstr(company).strip()
	if not company:
		frappe.throw(_("Set Company before analysing employee-cost history."))

	trailing_months = cint(trailing_months)
	if trailing_months < 1:
		frappe.throw(_("Trailing Months must be at least 1."))

	rows = frappe.get_all(
		"Employee Cost Entry",
		filters={"company": company},
		fields=EMPLOYEE_COST_HISTORY_FIELDS,
		order_by="cost_month desc, employee_name asc",
	)
	if not rows:
		frappe.throw(_("No employee-cost history is available for company {0}.").format(company))

	selected_months = get_trailing_cost_months(rows, trailing_months)
	return [
		row
		for row in rows
		if get_first_day(getdate(row.get("cost_month"))).isoformat() in selected_months
	]


def get_trailing_cost_months(rows: list[dict[str, Any]], trailing_months: int) -> set[str]:
	months: list[str] = []
	seen: set[str] = set()

	for row in rows:
		month_key = get_first_day(getdate(row.get("cost_month"))).isoformat()
		if month_key in seen:
			continue
		seen.add(month_key)
		months.append(month_key)
		if len(months) >= trailing_months:
			break

	return set(months)


def format_history_range(from_month: str | None, to_month: str | None) -> str | None:
	if not from_month or not to_month:
		return None
	if from_month == to_month:
		return formatdate(from_month, "MM-yyyy")
	return _("{0} to {1}").format(formatdate(from_month, "MM-yyyy"), formatdate(to_month, "MM-yyyy"))


def get_missing_company_cost_account_labels(document: Any) -> list[str]:
	return [
		spec["label"]
		for fieldname, spec in HR_ACCOUNT_FIELDS.items()
		if not cstr(get_document_value(document, fieldname)).strip()
	]


def validate_account_companies(document: Any, company: str) -> None:
	if not company:
		return

	for fieldname, spec in HR_ACCOUNT_FIELDS.items():
		account = cstr(get_document_value(document, fieldname)).strip()
		if not account:
			continue

		account_company = frappe.get_cached_value("Account", account, "company")
		if account_company and account_company != company:
			frappe.throw(_("{0} must belong to company {1}.").format(spec["label"], company))

	validate_contract_type_accounts(document, company)


def validate_contract_type_accounts(document: Any, company: str) -> None:
	seen = set()
	for row in get_document_value(document, "fab_hri_contract_type_accounts") or []:
		contract_type = cstr(get_document_value(row, "contract_type")).strip().upper()
		if contract_type in seen:
			frappe.throw(
				_("Contract type {0} is listed more than once in Accounts per Contract Type.").format(
					contract_type
				)
			)
		seen.add(contract_type)

		for fieldname in CONTRACT_TYPE_ACCOUNT_FIELDS:
			account = cstr(get_document_value(row, fieldname)).strip()
			if not account:
				continue
			if fieldname.endswith("_expense_account"):
				if not is_company_ledger(account, company, "Expense"):
					frappe.throw(
						_("Contract type {0}: {1} must be an enabled Expense ledger of company {2}.").format(
							contract_type, account, company
						)
					)
			elif not is_company_ledger(account, company, "Liability"):
				frappe.throw(
					_("Contract type {0}: {1} must be an enabled Liability ledger of company {2}.").format(
						contract_type, account, company
					)
				)


def is_company_ledger(account: str, company: str, root_type: str) -> bool:
	values = frappe.get_cached_value(
		"Account", account, ["company", "is_group", "root_type", "disabled"], as_dict=True
	)
	return bool(
		values
		and values.company == company
		and not values.is_group
		and not values.disabled
		and values.root_type == root_type
	)


def ensure_default_expense_account(company: str, account_name: str) -> str:
	existing = frappe.db.get_value(
		"Account",
		{"company": company, "root_type": "Expense", "account_name": account_name},
		"name",
	)
	if existing:
		return existing

	parent_account = get_default_expense_parent(company)
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"account_name": account_name,
			"parent_account": parent_account,
			"report_type": "Profit and Loss",
			"root_type": "Expense",
			"is_group": 0,
		}
	)
	account.flags.ignore_links = True
	account.flags.ignore_validate = True
	account.insert(ignore_permissions=True, ignore_mandatory=True, ignore_if_duplicate=True)
	return account.name


def ensure_default_liability_account(company: str, account_name: str) -> str:
	existing = frappe.db.get_value(
		"Account",
		{"company": company, "root_type": "Liability", "account_name": account_name},
		"name",
	)
	if existing:
		ensure_account_type(existing, "Payable")
		return existing

	account = get_or_create_account(
		company,
		{
			"account_name": account_name,
			"root_type": "Liability",
		},
	)
	ensure_account_type(account.name, "Payable")
	return account.name


def normalize_company_cost_payable_accounts(document: Any) -> None:
	for fieldname in (
		"default_payroll_payable_account",
		"fab_hri_employer_contribution_payable_account",
		"fab_hri_employer_insurance_payable_account",
		"fab_hri_tfr_payable_account",
	):
		account = cstr(get_document_value(document, fieldname)).strip()
		if account:
			ensure_account_type(account, "Payable")


def ensure_account_type(account: str, expected_account_type: str) -> None:
	current_account_type = cstr(frappe.db.get_value("Account", account, "account_type")).strip()
	if current_account_type == expected_account_type:
		return

	if current_account_type not in {"", "Tax"}:
		frappe.throw(
			_("Account {0} must use account type {1}.").format(account, expected_account_type)
		)

	frappe.db.set_value(
		"Account",
		account,
		"account_type",
		expected_account_type,
		update_modified=False,
	)


def get_default_expense_parent(company: str) -> str:
	parent_account = frappe.db.get_value(
		"Account",
		{"company": company, "root_type": "Expense", "account_name": "Indirect Expenses", "is_group": 1},
		"name",
	)
	if parent_account:
		return parent_account

	root_accounts = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"root_type": "Expense",
			"is_group": 1,
			"report_type": "Profit and Loss",
			"parent_account": ("is", "not set"),
		},
		pluck="name",
		limit=1,
	)
	if root_accounts:
		return root_accounts[0]

	frappe.throw(f"Could not determine an expense parent account for company {company}.")


def get_document_value(document: Any, fieldname: str) -> Any:
	getter = getattr(document, "get", None)
	if callable(getter):
		return getter(fieldname)
	return getattr(document, fieldname, None)
