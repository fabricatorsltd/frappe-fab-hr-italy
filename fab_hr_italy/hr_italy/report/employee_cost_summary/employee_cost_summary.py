from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_first_day, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	data = get_data(filters)
	return get_columns(), data, None, build_chart_data(data), build_report_summary(data)


def validate_filters(filters):
	if filters.get("from_month") and filters.get("to_month"):
		if get_first_day(getdate(filters.from_month)) > get_first_day(getdate(filters.to_month)):
			frappe.throw(_("From Month cannot be after To Month."))


def get_data(filters):
	query_filters = {}
	from_month = get_first_day(getdate(filters.from_month)) if filters.get("from_month") else None
	to_month = get_first_day(getdate(filters.to_month)) if filters.get("to_month") else None

	if filters.get("company"):
		query_filters["company"] = filters.company
	if filters.get("employee"):
		query_filters["employee"] = filters.employee
	if filters.get("source_type"):
		query_filters["source_type"] = filters.source_type
	if from_month and to_month:
		query_filters["cost_month"] = ["between", [from_month, to_month]]
	elif from_month:
		query_filters["cost_month"] = [">=", from_month]
	elif to_month:
		query_filters["cost_month"] = ["<=", to_month]

	rows = frappe.get_all(
		"Employee Cost Entry",
		filters=query_filters,
		fields=[
			"name",
			"company",
			"cost_month",
			"employee",
			"employee_name",
			"employee_identifier",
			"source_type",
			"contract_kind",
			"contract_type",
			"gross_monthly_amount",
			"employer_contribution_amount",
			"inail_amount",
			"tfr_accrual_amount",
			"expense_reimbursement_amount",
			"total_company_cost",
			"residual_value_amount",
			"tfr_balance_amount",
			"currency",
		],
		order_by="cost_month asc, employee_name asc",
	)

	for row in rows:
		row["cost_month_label"] = format_month_label(row.get("cost_month"))

	apply_missing_tfr_balance_fallback(rows)
	return rows


def apply_missing_tfr_balance_fallback(rows: list[dict]) -> None:
	employees_with_imported_tfr_balance = {
		get_employee_row_key(row) for row in rows if flt(row.get("tfr_balance_amount"))
	}
	running_balances: defaultdict[str, float] = defaultdict(float)

	for row in rows:
		employee_key = get_employee_row_key(row)
		if employee_key in employees_with_imported_tfr_balance:
			continue

		running_balances[employee_key] = flt(running_balances[employee_key]) + flt(
			row.get("tfr_accrual_amount")
		)
		row["tfr_balance_amount"] = round(flt(running_balances[employee_key]), 2)


def get_employee_row_key(row: dict) -> str:
	return (
		str(row.get("employee") or "").strip()
		or str(row.get("employee_identifier") or "").strip()
		or str(row.get("employee_name") or "").strip()
	)


def get_columns():
	# Kept to the monthly cost breakdown so the table stays readable; the identity,
	# contract and balance fields still live on each Employee Cost Entry.
	return [
		{
			"fieldname": "cost_month_label",
			"label": _("Month"),
			"fieldtype": "Data",
			"width": 85,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee"),
			"fieldtype": "Data",
			"width": 190,
		},
		{
			"fieldname": "gross_monthly_amount",
			"label": _("Gross"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "employer_contribution_amount",
			"label": _("Contributions"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "inail_amount",
			"label": _("INAIL"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 90,
		},
		{
			"fieldname": "tfr_accrual_amount",
			"label": _("TFR"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "expense_reimbursement_amount",
			"label": _("Reimbursements"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "total_company_cost",
			"label": _("Total Company Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 190,
		},
	]


def build_chart_data(rows):
	monthly_totals = build_monthly_totals(rows)
	if not monthly_totals:
		return None

	labels = list(monthly_totals)
	total_company_costs = [monthly_totals[label]["total_company_cost"] for label in labels]
	gross_amounts = [monthly_totals[label]["gross_monthly_amount"] for label in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Total Company Cost"), "values": total_company_costs},
				{"name": _("Gross Monthly Amount"), "values": gross_amounts},
			],
		},
		"type": "line",
		"colors": ["#2490ef", "#8e44ad"],
	}


def build_monthly_totals(rows: Iterable[dict]) -> dict[str, dict[str, float]]:
	monthly_totals: defaultdict[str, dict[str, float]] = defaultdict(
		lambda: {"total_company_cost": 0.0, "gross_monthly_amount": 0.0}
	)

	for row in rows:
		label = format_month_label(row.get("cost_month"))
		monthly_totals[label]["total_company_cost"] += flt(row.get("total_company_cost"))
		monthly_totals[label]["gross_monthly_amount"] += flt(row.get("gross_monthly_amount"))

	return {
		label: {
			"total_company_cost": flt(values["total_company_cost"], 2),
			"gross_monthly_amount": flt(values["gross_monthly_amount"], 2),
		}
		for label, values in monthly_totals.items()
	}


def build_report_summary(rows):
	if not rows:
		return None

	currency = rows[0].get("currency")

	return [
		{
			"value": sum(flt(row.get("total_company_cost")) for row in rows),
			"indicator": "Blue",
			"label": _("Total Company Cost"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": sum(flt(row.get("gross_monthly_amount")) for row in rows),
			"indicator": "Green",
			"label": _("Total Gross Pay"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": sum(flt(row.get("employer_contribution_amount")) for row in rows),
			"indicator": "Orange",
			"label": _("Total Employer Contributions"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": sum(flt(row.get("tfr_accrual_amount")) for row in rows),
			"indicator": "Purple",
			"label": _("Total TFR Accrual"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": len(rows),
			"indicator": "Grey",
			"label": _("Total Entries"),
			"datatype": "Int",
		},
	]


def format_month_label(value):
	return formatdate(get_first_day(getdate(value)), "MM-yyyy")
