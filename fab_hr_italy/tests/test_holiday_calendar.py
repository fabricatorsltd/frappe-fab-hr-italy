from __future__ import annotations

import unittest
from datetime import date

from fab_hr_italy.holiday_calendar import (
	build_italian_holiday_rows,
	calculate_easter_sunday,
	iter_italian_public_holidays,
	normalize_existing_holiday_dates,
)


class TestHolidayCalendar(unittest.TestCase):
	def test_calculate_easter_sunday(self):
		self.assertEqual(calculate_easter_sunday(2026), date(2026, 4, 5))
		self.assertEqual(calculate_easter_sunday(2027), date(2027, 3, 28))

	def test_iter_italian_public_holidays_includes_easter_monday_and_fixed_days(self):
		holidays = dict(iter_italian_public_holidays(date(2026, 1, 1), date(2026, 12, 31)))

		self.assertIn(date(2026, 1, 1), holidays)
		self.assertIn(date(2026, 4, 6), holidays)
		self.assertIn(date(2026, 6, 2), holidays)
		self.assertIn(date(2026, 12, 26), holidays)
		self.assertNotIn(date(2026, 4, 5), holidays)

	def test_build_italian_holiday_rows_adds_public_holidays_and_weekly_offs(self):
		rows = build_italian_holiday_rows(
			from_date="2026-04-01",
			to_date="2026-04-30",
			weekly_off="Sunday",
			existing_holiday_dates=["2026-04-06"],
		)

		holiday_dates = {row["holiday_date"] for row in rows}
		self.assertNotIn(date(2026, 4, 6), holiday_dates)
		self.assertIn(date(2026, 4, 12), holiday_dates)
		self.assertIn(date(2026, 4, 19), holiday_dates)
		self.assertIn(date(2026, 4, 26), holiday_dates)
		easter_sunday_rows = [row for row in rows if row["holiday_date"] == date(2026, 4, 5)]
		self.assertEqual(len(easter_sunday_rows), 1)
		self.assertEqual(easter_sunday_rows[0]["weekly_off"], 1)

	def test_normalize_existing_holiday_dates_accepts_json_array_string(self):
		self.assertEqual(
			normalize_existing_holiday_dates('["2026-04-06", "2026-04-25"]'),
			["2026-04-06", "2026-04-25"],
		)
