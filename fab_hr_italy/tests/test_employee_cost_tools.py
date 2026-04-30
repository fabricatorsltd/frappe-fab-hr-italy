from __future__ import annotations

import unittest
from datetime import date

from fab_hr_italy.hr_italy.doctype.employee_cost_entry.employee_cost_entry import (
	apply_employee_defaults,
	derive_missing_amounts,
	normalize_cost_month,
)
from fab_hr_italy.hr_italy.report.employee_cost_summary.employee_cost_summary import (
	build_monthly_totals,
	build_report_summary,
)


class TestEmployeeCostTools(unittest.TestCase):
	def test_normalize_cost_month_uses_first_day_of_month(self):
		self.assertEqual(normalize_cost_month("2025-12-28"), date(2025, 12, 1))

	def test_derive_missing_amounts_builds_direct_and_total_cost(self):
		values = derive_missing_amounts(
			{
				"gross_monthly_amount": 1805.69,
				"employer_contribution_amount": 581.29,
				"inail_amount": 7.29,
				"indirect_cost_accrued_amount": 727.32,
				"indirect_cost_paid_amount": 184.01,
			}
		)

		self.assertAlmostEqual(values["direct_cost_amount"], 2394.27)
		self.assertAlmostEqual(values["total_company_cost"], 2937.58)

	def test_apply_employee_defaults_uses_hrms_master_data(self):
		values = apply_employee_defaults(
			{
				"employee": "HR-EMP-00001",
				"workplace": "Imported Workplace",
				"job_title": "Imported Role",
			},
			{
				"name": "HR-EMP-00001",
				"company": "fabricators",
				"employee_name": "Pietro",
				"employee_number": "",
				"branch": "Brescia",
				"designation": "Chief Executive Officer",
				"department": "Management - fab",
				"employment_type": "Full-time",
				"date_of_joining": "2026-01-01",
				"contract_end_date": "2026-12-31",
			},
			overwrite=True,
		)

		self.assertEqual(values["company"], "fabricators")
		self.assertEqual(values["employee_name"], "Pietro")
		self.assertEqual(values["employee_identifier"], "HR-EMP-00001")
		self.assertEqual(values["workplace"], "Brescia")
		self.assertEqual(values["job_title"], "Chief Executive Officer")
		self.assertEqual(values["department_name"], "Management - fab")
		self.assertEqual(values["contract_kind"], "Full-time")
		self.assertEqual(values["contract_start_date"], "2026-01-01")
		self.assertEqual(values["contract_end_date"], "2026-12-31")

	def test_build_monthly_totals_aggregates_same_month_rows(self):
		monthly_totals = build_monthly_totals(
			[
				{"cost_month": "2025-12-01", "gross_monthly_amount": 100.123, "total_company_cost": 160.001},
				{
					"cost_month": date(2025, 12, 1),
					"gross_monthly_amount": 200.557,
					"total_company_cost": 340.67999999999995,
				},
			]
		)

		self.assertEqual(monthly_totals["12-2025"]["gross_monthly_amount"], 300.68)
		self.assertEqual(monthly_totals["12-2025"]["total_company_cost"], 500.68)

	def test_build_report_summary_returns_currency_totals(self):
		summary = build_report_summary(
			[
				{
					"currency": "EUR",
					"gross_monthly_amount": 100,
					"employer_contribution_amount": 20,
					"tfr_accrual_amount": 5,
					"total_company_cost": 130,
				},
				{
					"currency": "EUR",
					"gross_monthly_amount": 200,
					"employer_contribution_amount": 40,
					"tfr_accrual_amount": 10,
					"total_company_cost": 260,
				},
			]
		)

		self.assertEqual(summary[0]["value"], 390)
		self.assertEqual(summary[1]["value"], 300)
		self.assertEqual(summary[2]["value"], 60)
		self.assertEqual(summary[3]["value"], 15)
		self.assertEqual(summary[4]["value"], 2)
