from __future__ import annotations

import unittest

from fab_hr_italy.hr_italy.report.employee_cost_summary.employee_cost_summary import (
	apply_missing_tfr_balance_fallback,
)


class TestEmployeeCostSummary(unittest.TestCase):
	def test_apply_missing_tfr_balance_fallback_builds_running_balance(self):
		rows = [
			{
				"employee_identifier": "EMP-001",
				"tfr_accrual_amount": 10,
				"tfr_balance_amount": 0,
			},
			{
				"employee_identifier": "EMP-002",
				"tfr_accrual_amount": 5,
				"tfr_balance_amount": 0,
			},
			{
				"employee_identifier": "EMP-001",
				"tfr_accrual_amount": 7.5,
				"tfr_balance_amount": 0,
			},
			{
				"employee_identifier": "EMP-002",
				"tfr_accrual_amount": -2,
				"tfr_balance_amount": 0,
			},
		]

		apply_missing_tfr_balance_fallback(rows)

		self.assertEqual(rows[0]["tfr_balance_amount"], 10.0)
		self.assertEqual(rows[1]["tfr_balance_amount"], 5.0)
		self.assertEqual(rows[2]["tfr_balance_amount"], 17.5)
		self.assertEqual(rows[3]["tfr_balance_amount"], 3.0)

	def test_apply_missing_tfr_balance_fallback_preserves_imported_balance(self):
		rows = [
			{
				"employee_identifier": "EMP-001",
				"tfr_accrual_amount": 10,
				"tfr_balance_amount": 100,
			},
			{
				"employee_identifier": "EMP-001",
				"tfr_accrual_amount": 7.5,
				"tfr_balance_amount": 0,
			},
			{
				"employee_identifier": "EMP-002",
				"tfr_accrual_amount": 5,
				"tfr_balance_amount": 0,
			},
		]

		apply_missing_tfr_balance_fallback(rows)

		self.assertEqual(rows[0]["tfr_balance_amount"], 100)
		self.assertEqual(rows[1]["tfr_balance_amount"], 0)
		self.assertEqual(rows[2]["tfr_balance_amount"], 5.0)
