from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import frappe
from frappe import _


HOOK_NAME = "fab_hr_italy_employee_cost_sources"


def get_core_employee_cost_sources() -> list[dict[str, Any]]:
	return [
		{
			"value": "Manual",
			"label": _("Manual"),
			"entry_mode": "single",
		},
	]


def get_employee_cost_sources() -> list[dict[str, Any]]:
	sources: list[dict[str, Any]] = []

	for hook_path in frappe.get_hooks(HOOK_NAME) or []:
		hook = frappe.get_attr(hook_path)
		for source in hook() or []:
			if source and source.get("value"):
				sources.append(source)

	return deduplicate_sources(sources)


def deduplicate_sources(sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
	seen: dict[str, dict[str, Any]] = {}

	for source in sources:
		seen[source["value"]] = source

	return list(seen.values())


@frappe.whitelist()
def get_employee_cost_source_config() -> dict[str, Any]:
	sources = get_employee_cost_sources()
	return {
		"sources": sources,
		"has_file_importers": any(source.get("entry_mode") == "file" for source in sources),
	}
