from __future__ import annotations

import unittest

from fab_hr_italy.company_costing import (
	CompanyCostConfig,
	EmployeeCompanyCostOverrides,
	apply_employee_company_cost_overrides,
	build_employee_cost_forecast,
	compute_company_cost_breakdown,
	serialize_employee_cost_history_summary,
	summarize_employee_cost_history,
)


class TestCompanyCosting(unittest.TestCase):
	def test_compute_company_cost_breakdown_from_gross_pay(self):
		config = CompanyCostConfig(
			enabled=True,
			employer_contribution_rate=30.0,
			employer_insurance_rate=1.5,
			tfr_rate=7.41,
		)

		breakdown = compute_company_cost_breakdown(1000, config)

		self.assertEqual(breakdown.basis_amount, 1000.0)
		self.assertEqual(breakdown.employer_contribution_amount, 300.0)
		self.assertEqual(breakdown.employer_insurance_amount, 15.0)
		self.assertEqual(breakdown.tfr_accrual_amount, 74.1)
		self.assertEqual(breakdown.total_company_cost, 1389.1)

	def test_disabled_configuration_returns_zero_breakdown(self):
		config = CompanyCostConfig(enabled=False, employer_contribution_rate=30.0, tfr_rate=7.41)

		breakdown = compute_company_cost_breakdown(1000, config)

		self.assertEqual(breakdown.basis_amount, 0.0)
		self.assertEqual(breakdown.total_company_cost, 0.0)

	def test_negative_basis_is_clamped_to_zero(self):
		config = CompanyCostConfig(enabled=True, employer_contribution_rate=30.0, tfr_rate=7.41)

		breakdown = compute_company_cost_breakdown(-250, config)

		self.assertEqual(breakdown.basis_amount, 0.0)
		self.assertEqual(breakdown.employer_contribution_amount, 0.0)
		self.assertEqual(breakdown.tfr_accrual_amount, 0.0)

	def test_employee_overrides_replace_company_rates(self):
		config = CompanyCostConfig(
			enabled=True,
			employer_contribution_rate=30.0,
			employer_insurance_rate=1.5,
			tfr_rate=7.41,
		)
		overrides = EmployeeCompanyCostOverrides(
			enabled=True,
			employer_contribution_rate=28.4,
			employer_insurance_rate=2.2,
			tfr_rate=6.91,
		)

		resolved = apply_employee_company_cost_overrides(config, overrides)

		self.assertEqual(resolved.employer_contribution_rate, 28.4)
		self.assertEqual(resolved.employer_insurance_rate, 2.2)
		self.assertEqual(resolved.tfr_rate, 6.91)

	def test_missing_employee_override_values_fall_back_to_company(self):
		config = CompanyCostConfig(
			enabled=True,
			employer_contribution_rate=30.0,
			employer_insurance_rate=1.5,
			tfr_rate=7.41,
		)
		overrides = EmployeeCompanyCostOverrides(enabled=True, employer_contribution_rate=27.0)

		resolved = apply_employee_company_cost_overrides(config, overrides)

		self.assertEqual(resolved.employer_contribution_rate, 27.0)
		self.assertEqual(resolved.employer_insurance_rate, 1.5)
		self.assertEqual(resolved.tfr_rate, 7.41)

	def test_disabled_employee_overrides_leave_company_config_unchanged(self):
		config = CompanyCostConfig(
			enabled=True,
			employer_contribution_rate=30.0,
			employer_insurance_rate=1.5,
			tfr_rate=7.41,
		)
		overrides = EmployeeCompanyCostOverrides(enabled=False, employer_contribution_rate=27.0)

		resolved = apply_employee_company_cost_overrides(config, overrides)

		self.assertEqual(resolved.employer_contribution_rate, 30.0)
		self.assertEqual(resolved.employer_insurance_rate, 1.5)
		self.assertEqual(resolved.tfr_rate, 7.41)

	def test_summarize_employee_cost_history_builds_weighted_rates(self):
		summary = summarize_employee_cost_history(
			[
				{
					"cost_month": "2025-10-01",
					"employee_identifier": "EMP-001",
					"source_type": "Jet HR",
					"gross_monthly_amount": 1000,
					"employer_contribution_amount": 300,
					"inail_amount": 10,
					"tfr_accrual_amount": 74.1,
					"total_company_cost": 1384.1,
					"currency": "EUR",
				},
				{
					"cost_month": "2025-10-01",
					"employee_identifier": "EMP-002",
					"source_type": "Jet HR",
					"gross_monthly_amount": 500,
					"employer_contribution_amount": 150,
					"inail_amount": 5,
					"tfr_accrual_amount": 37.05,
					"total_company_cost": 692.05,
					"currency": "EUR",
				},
				{
					"cost_month": "2025-11-01",
					"employee_identifier": "EMP-001",
					"source_type": "Jet HR",
					"gross_monthly_amount": 1200,
					"employer_contribution_amount": 360,
					"inail_amount": 12,
					"tfr_accrual_amount": 88.92,
					"total_company_cost": 1660.92,
					"currency": "EUR",
				},
			]
		)

		self.assertEqual(summary.month_count, 2)
		self.assertEqual(summary.entry_count, 3)
		self.assertEqual(summary.source_types, ("Jet HR",))
		self.assertEqual(summary.average_monthly_headcount, 1.5)
		self.assertEqual(summary.employer_contribution_rate, 30.0)
		self.assertEqual(summary.employer_insurance_rate, 1.0)
		self.assertEqual(summary.tfr_rate, 7.41)
		self.assertEqual(summary.average_monthly_total_company_cost, 1868.54)

	def test_build_employee_cost_forecast_multiplies_trailing_average(self):
		summary = summarize_employee_cost_history(
			[
				{
					"cost_month": "2025-10-01",
					"employee_identifier": "EMP-001",
					"source_type": "Jet HR",
					"gross_monthly_amount": 1000,
					"employer_contribution_amount": 300,
					"inail_amount": 10,
					"tfr_accrual_amount": 74.1,
					"total_company_cost": 1384.1,
					"currency": "EUR",
				},
				{
					"cost_month": "2025-11-01",
					"employee_identifier": "EMP-001",
					"source_type": "Jet HR",
					"gross_monthly_amount": 1200,
					"employer_contribution_amount": 360,
					"inail_amount": 12,
					"tfr_accrual_amount": 88.92,
					"total_company_cost": 1660.92,
					"currency": "EUR",
				},
			]
		)

		forecast = build_employee_cost_forecast(summary, forecast_months=3)

		self.assertEqual(forecast["forecast_months"], 3)
		self.assertEqual(forecast["projected_gross_monthly_amount"], 3300.0)
		self.assertEqual(forecast["projected_employer_contribution_amount"], 990.0)
		self.assertEqual(forecast["projected_employer_insurance_amount"], 33.0)
		self.assertEqual(forecast["projected_tfr_accrual_amount"], 244.53)
		self.assertEqual(forecast["projected_total_company_cost"], 4567.53)

	def test_serialize_employee_cost_history_summary_returns_plain_values(self):
		summary = summarize_employee_cost_history(
			[
				{
					"cost_month": "2025-10-01",
					"employee_identifier": "EMP-001",
					"source_type": "Jet HR",
					"gross_monthly_amount": 1000,
					"employer_contribution_amount": 300,
					"inail_amount": 10,
					"tfr_accrual_amount": 74.1,
					"total_company_cost": 1384.1,
					"currency": "EUR",
				}
			]
		)

		payload = serialize_employee_cost_history_summary(summary)

		self.assertEqual(payload["source_types"], ["Jet HR"])
		self.assertEqual(payload["from_month"], "2025-10-01")
		self.assertEqual(payload["to_month"], "2025-10-01")


if __name__ == "__main__":
	unittest.main()
