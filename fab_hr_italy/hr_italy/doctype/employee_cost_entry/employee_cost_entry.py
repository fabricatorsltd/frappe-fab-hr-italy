from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, getdate

from fab_hr_italy.employee_cost_accounting import (
	validate_employee_cost_entry_delete,
	validate_employee_cost_entry_posting_lock,
)


def normalize_cost_month(value: date | str | None) -> date | None:
	if not value:
		return None

	return get_first_day(getdate(value))


def derive_missing_amounts(values: dict[str, Any]) -> dict[str, Any]:
	result = dict(values)

	if result.get("direct_cost_amount") in (None, "") and any(
		result.get(fieldname) not in (None, "")
		for fieldname in ("gross_monthly_amount", "employer_contribution_amount", "inail_amount")
	):
		result["direct_cost_amount"] = (
			flt(result.get("gross_monthly_amount"))
			+ flt(result.get("employer_contribution_amount"))
			+ flt(result.get("inail_amount"))
		)

	if result.get("total_company_cost") in (None, "") and result.get("direct_cost_amount") not in (None, ""):
		result["total_company_cost"] = (
			flt(result.get("direct_cost_amount"))
			+ flt(result.get("indirect_cost_accrued_amount"))
			+ flt(result.get("expense_reimbursement_amount"))
			- flt(result.get("indirect_cost_paid_amount"))
		)

	return result


def apply_employee_defaults(
	values: dict[str, Any], employee_values: dict[str, Any], overwrite: bool = False
) -> dict[str, Any]:
	result = dict(values)
	employee_values = employee_values or {}

	field_map = {
		"company": "company",
		"employee_name": "employee_name",
		"workplace": "branch",
		"job_title": "designation",
		"department_name": "department",
		"contract_kind": "employment_type",
		"contract_start_date": "date_of_joining",
		"contract_end_date": "contract_end_date",
	}

	for target_field, employee_field in field_map.items():
		if overwrite:
			result[target_field] = employee_values.get(employee_field)
		elif not result.get(target_field) and employee_values.get(employee_field):
			result[target_field] = employee_values.get(employee_field)

	if overwrite:
		result["employee_identifier"] = employee_values.get("employee_number") or employee_values.get("name")
	elif not result.get("employee_identifier"):
		result["employee_identifier"] = employee_values.get("employee_number") or employee_values.get("name")

	return result


class EmployeeCostEntry(Document):
	def validate(self):
		self.cost_month = normalize_cost_month(self.cost_month)
		validate_employee_cost_entry_posting_lock(self)

		if self.employee:
			employee_values = frappe.db.get_value(
				"Employee",
				self.employee,
				[
					"name",
					"company",
					"employee_name",
					"employee_number",
					"branch",
					"designation",
					"department",
					"employment_type",
					"date_of_joining",
					"contract_end_date",
				],
				as_dict=True,
			)
			for fieldname, value in apply_employee_defaults(
				self.as_dict(), employee_values, overwrite=True
			).items():
				if self.meta.has_field(fieldname):
					self.set(fieldname, value)

		self.employee_identifier = (self.employee_identifier or "").strip().upper()

		if self.company and not self.currency:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")

		if not self.currency:
			frappe.throw(_("Set a company currency before saving Employee Cost Entry records."))

		derived_amounts = derive_missing_amounts(self.as_dict())
		for fieldname in ("direct_cost_amount", "total_company_cost"):
			if derived_amounts.get(fieldname) not in (None, ""):
				self.set(fieldname, derived_amounts[fieldname])

		self.validate_duplicate_snapshot()

	def validate_duplicate_snapshot(self):
		existing_name = frappe.db.exists(
			"Employee Cost Entry",
			{
				"company": self.company,
				"employee_identifier": self.employee_identifier,
				"cost_month": self.cost_month,
				"name": ["!=", self.name],
			},
		)
		if existing_name:
			frappe.throw(
				_(
					"An Employee Cost Entry already exists for employee {0} in {1} for {2}: {3}"
				).format(
					self.employee_identifier,
					self.company,
					frappe.format_value(self.cost_month, {"fieldtype": "Date"}),
					existing_name,
				)
			)

	def on_trash(self):
		validate_employee_cost_entry_delete(self)
