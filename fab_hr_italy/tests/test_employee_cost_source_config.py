from __future__ import annotations

import unittest
from unittest.mock import patch

from fab_hr_italy.hr_italy.employee_cost_sources import (
	deduplicate_sources,
	get_employee_cost_source_config,
	get_employee_cost_sources,
)


class TestEmployeeCostSourceConfig(unittest.TestCase):
	def test_deduplicate_sources_keeps_last_definition_per_value(self):
		sources = deduplicate_sources(
			[
				{"value": "Manual", "entry_mode": "single"},
				{"value": "Jet HR", "entry_mode": "file"},
				{"value": "Manual", "entry_mode": "file"},
			]
		)

		self.assertEqual(
			sources,
			[
				{"value": "Manual", "entry_mode": "file"},
				{"value": "Jet HR", "entry_mode": "file"},
			],
		)

	@patch("fab_hr_italy.hr_italy.employee_cost_sources.frappe.get_hooks")
	@patch("fab_hr_italy.hr_italy.employee_cost_sources.frappe.get_attr")
	def test_get_employee_cost_sources_collects_hooked_sources(self, mock_get_attr, mock_get_hooks):
		mock_get_hooks.return_value = [
			"fab_hr_italy.hr_italy.employee_cost_sources.get_core_employee_cost_sources",
			"fab_jethr_import.employee_cost_sources.get_jethr_employee_cost_sources",
		]
		mock_get_attr.side_effect = [
			lambda: [{"value": "Manual", "entry_mode": "single"}],
			lambda: [{"value": "Jet HR", "entry_mode": "file", "upload_method": "fab_jethr_import.api.upload"}],
		]

		sources = get_employee_cost_sources()

		self.assertEqual(
			sources,
			[
				{"value": "Manual", "entry_mode": "single"},
				{"value": "Jet HR", "entry_mode": "file", "upload_method": "fab_jethr_import.api.upload"},
			],
		)

	@patch("fab_hr_italy.hr_italy.employee_cost_sources.get_employee_cost_sources")
	def test_get_employee_cost_source_config_marks_file_importers(self, mock_get_sources):
		mock_get_sources.return_value = [{"value": "Manual", "entry_mode": "single"}]
		self.assertFalse(get_employee_cost_source_config()["has_file_importers"])

		mock_get_sources.return_value = [
			{"value": "Manual", "entry_mode": "single"},
			{"value": "Jet HR", "entry_mode": "file"},
		]
		self.assertTrue(get_employee_cost_source_config()["has_file_importers"])
