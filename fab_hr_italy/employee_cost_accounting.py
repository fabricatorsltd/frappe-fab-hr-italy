from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, formatdate, get_last_day

from fab_hr_italy.company_costing import CompanyCostConfig, get_company_cost_config

MONTH_ENTRY_FIELDS = [
	"name",
	"company",
	"cost_month",
	"currency",
	"gross_monthly_amount",
	"employer_contribution_amount",
	"inail_amount",
	"tfr_accrual_amount",
	"indirect_cost_accrued_amount",
	"indirect_cost_paid_amount",
	"accrual_journal_entry",
	"contract_type",
]
POSTING_LOCKED_FIELDS = (
	"company",
	"cost_month",
	"employee",
	"employee_name",
	"employee_identifier",
	"currency",
	"gross_monthly_amount",
	"employer_contribution_amount",
	"inail_amount",
	"tfr_accrual_amount",
	"accrual_journal_entry",
)
ACCOUNT_COMPONENTS = (
	(
		"gross_monthly_amount",
		"gross_pay_expense_account",
		"payroll_payable_account",
		_("gross pay"),
	),
	(
		"employer_contribution_amount",
		"employer_contribution_expense_account",
		"employer_contribution_payable_account",
		_("Employer contribution"),
	),
	(
		"inail_amount",
		"employer_insurance_expense_account",
		"employer_insurance_payable_account",
		_("Employer insurance"),
	),
	(
		"tfr_accrual_amount",
		"tfr_expense_account",
		"tfr_payable_account",
		_("TFR accrual"),
	),
)
CONTRACT_TYPE_ACCOUNTS_DOCTYPE = "Employee Cost Contract Type Account"
CONTRACT_TYPE_ACCOUNTS_FIELD = "fab_hri_contract_type_accounts"


@frappe.whitelist()
def post_employee_cost_month_to_gl(employee_cost_entry: str) -> dict[str, Any]:
	entry = frappe.get_doc("Employee Cost Entry", employee_cost_entry)
	rows = get_month_employee_cost_rows(entry.company, entry.cost_month)
	submitted_journal_entries = get_submitted_journal_entries(rows)
	if submitted_journal_entries:
		posted_rows = [
			row
			for row in rows
			if row.get("accrual_journal_entry") and row["accrual_journal_entry"] in submitted_journal_entries
		]
		if len(posted_rows) != len(rows):
			frappe.throw(
				_("Employee-cost month {0} for company {1} is only partially linked to submitted Journal Entries.").format(
					formatdate(entry.cost_month, "MM-yyyy"),
					entry.company,
				)
			)
		if len(submitted_journal_entries) > 1:
			frappe.throw(
				_("Employee-cost month {0} for company {1} is already linked to multiple submitted Journal Entries.").format(
					formatdate(entry.cost_month, "MM-yyyy"),
					entry.company,
				)
			)
		journal_entry = sorted(submitted_journal_entries)[0]
		return {
			"journal_entry": journal_entry,
			"route": ["Form", "Journal Entry", journal_entry],
			"message": _("Employee-cost accrual is already posted in Journal Entry {0}.").format(
				journal_entry
			),
		}

	config = ensure_employee_cost_gl_posting_enabled(entry.company)
	accounts = build_employee_cost_accrual_accounts(
		rows,
		config,
		get_company_cost_center(entry.company),
		get_contract_type_accounts(entry.company),
	)
	if not accounts:
		frappe.throw(_("No employee-cost accrual amounts are available to post for {0}.").format(
			formatdate(entry.cost_month, "MM-yyyy")
		))

	journal_entry = create_employee_cost_accrual_journal_entry(
		company=entry.company,
		cost_month=entry.cost_month,
		currency=entry.currency,
		accounts=accounts,
	)
	for row in rows:
		frappe.db.set_value(
			"Employee Cost Entry",
			row["name"],
			"accrual_journal_entry",
			journal_entry.name,
			update_modified=False,
		)
	return {
		"journal_entry": journal_entry.name,
		"route": ["Form", "Journal Entry", journal_entry.name],
		"posted_entries": len(rows),
		"message": _("Posted employee-cost accrual for {0} into Journal Entry {1}.").format(
			formatdate(entry.cost_month, "MM-yyyy"),
			journal_entry.name,
		),
	}


def ensure_employee_cost_gl_posting_enabled(company: str) -> CompanyCostConfig:
	config = get_company_cost_config(company)
	if not (config.enabled and config.post_to_payroll_entry):
		frappe.throw(_("Enable payroll-entry posting on Company {0} before posting employee cost to GL.").format(company))

	missing_labels = []
	for _fieldname, expense_attr, payable_attr, label in ACCOUNT_COMPONENTS:
		if not getattr(config, expense_attr):
			missing_labels.append(_("Missing expense account for {0}.").format(label))
		if not getattr(config, payable_attr):
			missing_labels.append(_("Missing payable account for {0}.").format(label))
	if missing_labels:
		frappe.throw(" ".join(missing_labels))

	return config


def get_month_employee_cost_rows(company: str, cost_month) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Employee Cost Entry",
		filters={"company": company, "cost_month": cost_month},
		fields=MONTH_ENTRY_FIELDS,
		order_by="employee_name asc, name asc",
	)
	if not rows:
		frappe.throw(
			_("No Employee Cost Entry rows are available for company {0} in {1}.").format(
				company,
				formatdate(cost_month, "MM-yyyy"),
			)
		)
	return rows


def get_submitted_journal_entries(rows: list[dict[str, Any]]) -> set[str]:
	journal_entries = sorted({row.get("accrual_journal_entry") for row in rows if row.get("accrual_journal_entry")})
	if not journal_entries:
		return set()
	return set(
		frappe.get_all(
			"Journal Entry",
			filters={"name": ["in", journal_entries], "docstatus": 1},
			pluck="name",
		)
	)


def get_contract_type_accounts(company: str) -> dict[str, dict[str, str]]:
	account_fields = [attr for _field, expense, payable, _label in ACCOUNT_COMPONENTS for attr in (expense, payable)]
	rows = frappe.get_all(
		CONTRACT_TYPE_ACCOUNTS_DOCTYPE,
		filters={"parenttype": "Company", "parent": company, "parentfield": CONTRACT_TYPE_ACCOUNTS_FIELD},
		fields=["contract_type", *account_fields],
		order_by="idx asc",
	)
	return {
		normalize_contract_type(row.get("contract_type")): {
			fieldname: row[fieldname] for fieldname in account_fields if row.get(fieldname)
		}
		for row in rows
		if normalize_contract_type(row.get("contract_type"))
	}


def normalize_contract_type(value: Any) -> str:
	return cstr(value).strip().upper()


def build_employee_cost_accrual_accounts(
	rows: list[dict[str, Any]],
	config: CompanyCostConfig,
	cost_center: str | None,
	contract_type_accounts: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
	account_rows: dict[tuple[str, str], dict[str, Any]] = {}
	contract_type_accounts = contract_type_accounts or {}

	def add_component(get_amount, expense_attr: str, payable_attr: str) -> None:
		# rows sharing the same account pair are summed before rounding, so a month
		# without contract type overrides posts exactly the totals it always did
		amounts: dict[tuple[str, str], list[float]] = {}
		for row in rows:
			overrides = contract_type_accounts.get(normalize_contract_type(row.get("contract_type"))) or {}
			key = (
				overrides.get(expense_attr) or getattr(config, expense_attr),
				overrides.get(payable_attr) or getattr(config, payable_attr),
			)
			amounts.setdefault(key, []).append(get_amount(row))

		for (expense_account, payable_account), key_amounts in amounts.items():
			total_amount = round(sum(key_amounts), 2)
			if not total_amount:
				continue
			add_accounting_row(account_rows, expense_account, "debit", total_amount, cost_center)
			add_accounting_row(account_rows, payable_account, "credit", total_amount, cost_center)

	for amount_field, expense_attr, payable_attr, _label in ACCOUNT_COMPONENTS:
		add_component(lambda row, field=amount_field: flt(row.get(field)), expense_attr, payable_attr)

	add_component(get_other_employee_accrual_amount, "gross_pay_expense_account", "payroll_payable_account")

	return list(account_rows.values())


def add_accounting_row(
	account_rows: dict[tuple[str, str], dict[str, Any]],
	account: str,
	entry_type: str,
	amount: float,
	cost_center: str | None,
) -> None:
	key = (account, entry_type)
	row = account_rows.setdefault(
		key,
		{
			"account": account,
			"debit_in_account_currency": 0.0,
			"credit_in_account_currency": 0.0,
		},
	)
	if cost_center:
		row["cost_center"] = cost_center
	row[f"{entry_type}_in_account_currency"] = round(
		row.get(f"{entry_type}_in_account_currency", 0.0) + amount,
		2,
	)


def get_other_employee_accrual_amount(row: dict[str, Any]) -> float:
	indirect_cost_accrued_amount = flt(row.get("indirect_cost_accrued_amount"))
	indirect_cost_paid_amount = flt(row.get("indirect_cost_paid_amount"))
	if not indirect_cost_accrued_amount and not indirect_cost_paid_amount:
		return 0.0
	return indirect_cost_accrued_amount - flt(row.get("tfr_accrual_amount")) - indirect_cost_paid_amount


def create_employee_cost_accrual_journal_entry(
	company: str,
	cost_month,
	currency: str | None,
	accounts: list[dict[str, Any]],
):
	journal_entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": company,
			"posting_date": get_last_day(cost_month),
			"party_not_required": 1,
			"user_remark": _("Employee cost accrual for {0}.").format(
				formatdate(cost_month, "MM-yyyy")
			),
			"accounts": accounts,
			"multi_currency": cint(bool(currency and currency != frappe.get_cached_value("Company", company, "default_currency"))),
		}
	)
	journal_entry.insert(ignore_permissions=True)
	try:
		journal_entry.submit()
	except Exception:
		cleanup_failed_employee_cost_accrual_journal_entry(journal_entry.name)
		raise
	return journal_entry


def cleanup_failed_employee_cost_accrual_journal_entry(journal_entry_name: str) -> None:
	journal_entry_name = cstr(journal_entry_name).strip()
	if not journal_entry_name or not frappe.db.exists("Journal Entry", journal_entry_name):
		return

	docstatus = cint(frappe.db.get_value("Journal Entry", journal_entry_name, "docstatus"))
	has_gl_entries = bool(
		frappe.db.exists(
			"GL Entry",
			{
				"voucher_type": "Journal Entry",
				"voucher_no": journal_entry_name,
				"is_cancelled": 0,
			},
		)
	)
	if docstatus == 1 and has_gl_entries:
		frappe.get_doc("Journal Entry", journal_entry_name).cancel()
		return

	if docstatus == 1:
		frappe.db.set_value("Journal Entry", journal_entry_name, "docstatus", 0, update_modified=False)
	frappe.delete_doc("Journal Entry", journal_entry_name, ignore_permissions=True, force=1)


def get_company_cost_center(company: str) -> str | None:
	return cstr(frappe.db.get_value("Company", company, "cost_center")).strip() or None


def validate_employee_cost_entry_posting_lock(document) -> None:
	if document.is_new():
		return

	previous = document.get_doc_before_save()
	if not previous or not cstr(previous.accrual_journal_entry).strip():
		return

	if cint(frappe.db.get_value("Journal Entry", previous.accrual_journal_entry, "docstatus")) != 1:
		return

	changed_fields = [
		fieldname for fieldname in POSTING_LOCKED_FIELDS if document.get(fieldname) != previous.get(fieldname)
	]
	if changed_fields:
		frappe.throw(
			_("Cancel linked Journal Entry {0} before changing posted employee-cost data.").format(
				previous.accrual_journal_entry
			)
		)
	document.accrual_journal_entry = previous.accrual_journal_entry


def validate_employee_cost_entry_delete(document) -> None:
	journal_entry = cstr(document.accrual_journal_entry).strip()
	if not journal_entry:
		return
	if cint(frappe.db.get_value("Journal Entry", journal_entry, "docstatus")) == 1:
		frappe.throw(
			_("Cancel linked Journal Entry {0} before deleting this posted Employee Cost Entry.").format(
				journal_entry
			)
		)
