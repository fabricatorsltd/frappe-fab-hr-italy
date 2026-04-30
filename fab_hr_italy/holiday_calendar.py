from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Iterable

import frappe
from frappe import _
from frappe.utils import getdate

ITALIAN_FIXED_HOLIDAYS = {
	(1, 1): _("New Year's Day"),
	(1, 6): _("Epiphany"),
	(4, 25): _("Liberation Day"),
	(5, 1): _("Labour Day"),
	(6, 2): _("Republic Day"),
	(8, 15): _("Assumption Day"),
	(11, 1): _("All Saints' Day"),
	(12, 8): _("Immaculate Conception"),
	(12, 25): _("Christmas Day"),
	(12, 26): _("St. Stephen's Day"),
}

WEEKDAY_INDEX_BY_NAME = {
	"Monday": 0,
	"Tuesday": 1,
	"Wednesday": 2,
	"Thursday": 3,
	"Friday": 4,
	"Saturday": 5,
	"Sunday": 6,
}


@frappe.whitelist()
def build_italian_holiday_rows(
	from_date: str,
	to_date: str,
	weekly_off: str | None = None,
	is_half_day: int = 0,
	existing_holiday_dates: list[str] | None = None,
) -> list[dict[str, object]]:
	start_date = getdate(from_date)
	end_date = getdate(to_date)
	if start_date > end_date:
		frappe.throw(_("To Date cannot be before From Date"))

	existing_dates = {
		getdate(value) for value in normalize_existing_holiday_dates(existing_holiday_dates) if value
	}
	rows: list[dict[str, object]] = []

	for holiday_date, description in iter_italian_public_holidays(start_date, end_date):
		if holiday_date in existing_dates:
			continue
		rows.append(
			{
				"holiday_date": holiday_date,
				"description": description,
				"weekly_off": 0,
				"is_half_day": 0,
			}
		)
		existing_dates.add(holiday_date)

	if weekly_off:
		for weekly_off_date in iter_weekly_off_dates(start_date, end_date, weekly_off):
			if weekly_off_date in existing_dates:
				continue
			rows.append(
				{
					"holiday_date": weekly_off_date,
					"description": _(weekly_off),
					"weekly_off": 1,
					"is_half_day": 1 if is_half_day else 0,
				}
			)
			existing_dates.add(weekly_off_date)

	rows.sort(key=lambda row: getdate(row["holiday_date"]))
	return rows


def normalize_existing_holiday_dates(existing_holiday_dates) -> list[str]:
	if not existing_holiday_dates:
		return []

	if isinstance(existing_holiday_dates, str):
		loaded_value = json.loads(existing_holiday_dates)
		if isinstance(loaded_value, list):
			return loaded_value
		return [loaded_value]

	if isinstance(existing_holiday_dates, tuple):
		return list(existing_holiday_dates)

	return existing_holiday_dates


def iter_italian_public_holidays(start_date: date, end_date: date) -> Iterable[tuple[date, str]]:
	for year in range(start_date.year, end_date.year + 1):
		for (month, day), description in ITALIAN_FIXED_HOLIDAYS.items():
			holiday_date = date(year, month, day)
			if start_date <= holiday_date <= end_date:
				yield holiday_date, description

		easter_monday = calculate_easter_sunday(year) + timedelta(days=1)
		if start_date <= easter_monday <= end_date:
			yield easter_monday, _("Easter Monday")


def iter_weekly_off_dates(start_date: date, end_date: date, weekly_off: str) -> Iterable[date]:
	weekday_index = WEEKDAY_INDEX_BY_NAME.get(weekly_off)
	if weekday_index is None:
		return []

	current_date = start_date
	while current_date <= end_date:
		if current_date.weekday() == weekday_index:
			yield current_date
		current_date += timedelta(days=1)


def calculate_easter_sunday(year: int) -> date:
	a = year % 19
	b = year // 100
	c = year % 100
	d = b // 4
	e = b % 4
	f = (b + 8) // 25
	g = (b - f + 1) // 3
	h = (19 * a + b - d - g + 15) % 30
	i = c // 4
	k = c % 4
	l = (32 + 2 * e + 2 * i - h - k) % 7
	m = (a + 11 * h + 22 * l) // 451
	month = (h + l - 7 * m + 114) // 31
	day = ((h + l - 7 * m + 114) % 31) + 1
	return date(year, month, day)
