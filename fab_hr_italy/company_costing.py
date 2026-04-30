from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP

from frappe.utils import flt, get_first_day, getdate


@dataclass(frozen=True)
class CompanyCostConfig:
	enabled: bool = False
	basis_mode: str = "Gross Pay"
	employer_contribution_rate: float = 0.0
	employer_insurance_rate: float = 0.0
	tfr_rate: float = 0.0
	post_to_payroll_entry: bool = False
	gross_pay_expense_account: str | None = None
	payroll_payable_account: str | None = None
	employer_contribution_expense_account: str | None = None
	employer_contribution_payable_account: str | None = None
	employer_insurance_expense_account: str | None = None
	employer_insurance_payable_account: str | None = None
	tfr_expense_account: str | None = None
	tfr_payable_account: str | None = None


@dataclass(frozen=True)
class EmployeeCompanyCostOverrides:
	enabled: bool = False
	employer_contribution_rate: float | None = None
	employer_insurance_rate: float | None = None
	tfr_rate: float | None = None


@dataclass(frozen=True)
class CompanyCostBreakdown:
	basis_amount: float = 0.0
	employer_contribution_amount: float = 0.0
	employer_insurance_amount: float = 0.0
	tfr_accrual_amount: float = 0.0
	total_company_cost: float = 0.0


@dataclass(frozen=True)
class EmployeeCostHistorySummary:
	basis_mode: str = "Gross Pay"
	currency: str | None = None
	entry_count: int = 0
	month_count: int = 0
	from_month: str | None = None
	to_month: str | None = None
	source_types: tuple[str, ...] = ()
	total_gross_monthly_amount: float = 0.0
	total_employer_contribution_amount: float = 0.0
	total_employer_insurance_amount: float = 0.0
	total_tfr_accrual_amount: float = 0.0
	total_company_cost: float = 0.0
	average_monthly_gross_monthly_amount: float = 0.0
	average_monthly_employer_contribution_amount: float = 0.0
	average_monthly_employer_insurance_amount: float = 0.0
	average_monthly_tfr_accrual_amount: float = 0.0
	average_monthly_total_company_cost: float = 0.0
	average_monthly_headcount: float = 0.0
	employer_contribution_rate: float = 0.0
	employer_insurance_rate: float = 0.0
	tfr_rate: float = 0.0


def compute_company_cost_breakdown(
	basis_amount: float,
	config: CompanyCostConfig,
	precision: int = 2,
) -> CompanyCostBreakdown:
	if not config.enabled:
		return CompanyCostBreakdown()

	normalized_basis = _quantize(max(basis_amount, 0), precision)
	employer_contribution_amount = _quantize(
		normalized_basis * config.employer_contribution_rate / 100,
		precision,
	)
	employer_insurance_amount = _quantize(
		normalized_basis * config.employer_insurance_rate / 100,
		precision,
	)
	tfr_accrual_amount = _quantize(normalized_basis * config.tfr_rate / 100, precision)
	total_company_cost = _quantize(
		normalized_basis
		+ employer_contribution_amount
		+ employer_insurance_amount
		+ tfr_accrual_amount,
		precision,
	)

	return CompanyCostBreakdown(
		basis_amount=normalized_basis,
		employer_contribution_amount=employer_contribution_amount,
		employer_insurance_amount=employer_insurance_amount,
		tfr_accrual_amount=tfr_accrual_amount,
		total_company_cost=total_company_cost,
	)


def summarize_employee_cost_history(
	rows: list[dict],
	precision: int = 2,
) -> EmployeeCostHistorySummary:
	if not rows:
		raise ValueError("Employee cost history is empty.")

	monthly_totals: defaultdict = defaultdict(
		lambda: {
			"gross_monthly_amount": 0.0,
			"employer_contribution_amount": 0.0,
			"employer_insurance_amount": 0.0,
			"tfr_accrual_amount": 0.0,
			"total_company_cost": 0.0,
			"employees": set(),
		}
	)
	source_types: set[str] = set()
	currency = None

	for row in rows:
		month_key = get_first_day(getdate(row.get("cost_month")))
		monthly_totals[month_key]["gross_monthly_amount"] += flt(row.get("gross_monthly_amount"))
		monthly_totals[month_key]["employer_contribution_amount"] += flt(
			row.get("employer_contribution_amount")
		)
		monthly_totals[month_key]["employer_insurance_amount"] += flt(row.get("inail_amount"))
		monthly_totals[month_key]["tfr_accrual_amount"] += flt(row.get("tfr_accrual_amount"))
		monthly_totals[month_key]["total_company_cost"] += flt(row.get("total_company_cost"))
		employee_key = row.get("employee_identifier") or row.get("employee") or row.get("employee_name")
		if employee_key:
			monthly_totals[month_key]["employees"].add(employee_key)
		if row.get("source_type"):
			source_types.add(row["source_type"])
		currency = currency or row.get("currency")

	months = sorted(monthly_totals)
	month_count = len(months)
	total_gross = _quantize(
		sum(values["gross_monthly_amount"] for values in monthly_totals.values()),
		precision,
	)
	total_employer_contribution = _quantize(
		sum(values["employer_contribution_amount"] for values in monthly_totals.values()),
		precision,
	)
	total_employer_insurance = _quantize(
		sum(values["employer_insurance_amount"] for values in monthly_totals.values()),
		precision,
	)
	total_tfr = _quantize(sum(values["tfr_accrual_amount"] for values in monthly_totals.values()), precision)
	total_company_cost = _quantize(
		sum(values["total_company_cost"] for values in monthly_totals.values()),
		precision,
	)
	average_monthly_headcount = _quantize(
		sum(len(values["employees"]) for values in monthly_totals.values()) / month_count,
		1,
	)

	return EmployeeCostHistorySummary(
		basis_mode="Gross Pay",
		currency=currency,
		entry_count=len(rows),
		month_count=month_count,
		from_month=months[0].isoformat(),
		to_month=months[-1].isoformat(),
		source_types=tuple(sorted(source_types)),
		total_gross_monthly_amount=total_gross,
		total_employer_contribution_amount=total_employer_contribution,
		total_employer_insurance_amount=total_employer_insurance,
		total_tfr_accrual_amount=total_tfr,
		total_company_cost=total_company_cost,
		average_monthly_gross_monthly_amount=_quantize(total_gross / month_count, precision),
		average_monthly_employer_contribution_amount=_quantize(
			total_employer_contribution / month_count, precision
		),
		average_monthly_employer_insurance_amount=_quantize(total_employer_insurance / month_count, precision),
		average_monthly_tfr_accrual_amount=_quantize(total_tfr / month_count, precision),
		average_monthly_total_company_cost=_quantize(total_company_cost / month_count, precision),
		average_monthly_headcount=average_monthly_headcount,
		employer_contribution_rate=_calculate_weighted_rate(total_employer_contribution, total_gross, precision),
		employer_insurance_rate=_calculate_weighted_rate(total_employer_insurance, total_gross, precision),
		tfr_rate=_calculate_weighted_rate(total_tfr, total_gross, precision),
	)


def build_employee_cost_forecast(
	summary: EmployeeCostHistorySummary,
	forecast_months: int,
	precision: int = 2,
) -> dict[str, float | int]:
	if forecast_months < 1:
		raise ValueError("Forecast months must be at least 1.")

	return {
		"forecast_months": forecast_months,
		"projected_gross_monthly_amount": _quantize(
			summary.average_monthly_gross_monthly_amount * forecast_months,
			precision,
		),
		"projected_employer_contribution_amount": _quantize(
			summary.average_monthly_employer_contribution_amount * forecast_months,
			precision,
		),
		"projected_employer_insurance_amount": _quantize(
			summary.average_monthly_employer_insurance_amount * forecast_months,
			precision,
		),
		"projected_tfr_accrual_amount": _quantize(
			summary.average_monthly_tfr_accrual_amount * forecast_months,
			precision,
		),
		"projected_total_company_cost": _quantize(
			summary.average_monthly_total_company_cost * forecast_months,
			precision,
		),
	}


def serialize_employee_cost_history_summary(summary: EmployeeCostHistorySummary) -> dict[str, object]:
	return {
		**asdict(summary),
		"source_types": list(summary.source_types),
	}


def get_company_cost_config(company: str, employee: str | None = None) -> CompanyCostConfig:
	import frappe
	from frappe.utils import cint, flt

	values = frappe.db.get_value(
		"Company",
		company,
		[
			"fab_hri_enabled",
			"fab_hri_costing_basis",
			"fab_hri_employer_contribution_rate",
			"fab_hri_employer_insurance_rate",
			"fab_hri_tfr_rate",
			"fab_hri_post_company_cost_to_payroll_entry",
			"fab_hri_gross_pay_expense_account",
			"default_payroll_payable_account",
			"fab_hri_employer_contribution_expense_account",
			"fab_hri_employer_contribution_payable_account",
			"fab_hri_employer_insurance_expense_account",
			"fab_hri_employer_insurance_payable_account",
			"fab_hri_tfr_expense_account",
			"fab_hri_tfr_payable_account",
		],
		as_dict=True,
	) or {}

	config = CompanyCostConfig(
		enabled=bool(cint(values.get("fab_hri_enabled"))),
		basis_mode=values.get("fab_hri_costing_basis") or "Gross Pay",
		employer_contribution_rate=flt(values.get("fab_hri_employer_contribution_rate")),
		employer_insurance_rate=flt(values.get("fab_hri_employer_insurance_rate")),
		tfr_rate=flt(values.get("fab_hri_tfr_rate")),
		post_to_payroll_entry=bool(cint(values.get("fab_hri_post_company_cost_to_payroll_entry"))),
		gross_pay_expense_account=values.get("fab_hri_gross_pay_expense_account"),
		payroll_payable_account=values.get("default_payroll_payable_account"),
		employer_contribution_expense_account=values.get("fab_hri_employer_contribution_expense_account"),
		employer_contribution_payable_account=values.get("fab_hri_employer_contribution_payable_account"),
		employer_insurance_expense_account=values.get("fab_hri_employer_insurance_expense_account"),
		employer_insurance_payable_account=values.get("fab_hri_employer_insurance_payable_account"),
		tfr_expense_account=values.get("fab_hri_tfr_expense_account"),
		tfr_payable_account=values.get("fab_hri_tfr_payable_account"),
	)

	if not employee:
		return config

	return apply_employee_company_cost_overrides(config, get_employee_company_cost_overrides(employee))


def get_employee_company_cost_overrides(employee: str) -> EmployeeCompanyCostOverrides:
	import frappe
	from frappe.utils import cint, flt

	values = frappe.db.get_value(
		"Employee",
		employee,
		[
			"fab_hri_apply_employee_overrides",
			"fab_hri_employer_contribution_rate_override",
			"fab_hri_employer_insurance_rate_override",
			"fab_hri_tfr_rate_override",
		],
		as_dict=True,
	) or {}

	return EmployeeCompanyCostOverrides(
		enabled=bool(cint(values.get("fab_hri_apply_employee_overrides"))),
		employer_contribution_rate=_optional_rate(values.get("fab_hri_employer_contribution_rate_override"), flt),
		employer_insurance_rate=_optional_rate(values.get("fab_hri_employer_insurance_rate_override"), flt),
		tfr_rate=_optional_rate(values.get("fab_hri_tfr_rate_override"), flt),
	)


def apply_employee_company_cost_overrides(
	config: CompanyCostConfig,
	overrides: EmployeeCompanyCostOverrides,
) -> CompanyCostConfig:
	if not overrides.enabled:
		return config

	return CompanyCostConfig(
		enabled=config.enabled,
		basis_mode=config.basis_mode,
		employer_contribution_rate=(
			overrides.employer_contribution_rate
			if overrides.employer_contribution_rate is not None
			else config.employer_contribution_rate
		),
		employer_insurance_rate=(
			overrides.employer_insurance_rate
			if overrides.employer_insurance_rate is not None
			else config.employer_insurance_rate
		),
		tfr_rate=overrides.tfr_rate if overrides.tfr_rate is not None else config.tfr_rate,
		post_to_payroll_entry=config.post_to_payroll_entry,
		gross_pay_expense_account=config.gross_pay_expense_account,
		payroll_payable_account=config.payroll_payable_account,
		employer_contribution_expense_account=config.employer_contribution_expense_account,
		employer_contribution_payable_account=config.employer_contribution_payable_account,
		employer_insurance_expense_account=config.employer_insurance_expense_account,
		employer_insurance_payable_account=config.employer_insurance_payable_account,
		tfr_expense_account=config.tfr_expense_account,
		tfr_payable_account=config.tfr_payable_account,
	)


def _quantize(value: float, precision: int) -> float:
	quantizer = Decimal("1") if precision <= 0 else Decimal(f"1.{'0' * precision}")
	return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP))


def _calculate_weighted_rate(amount: float, basis_amount: float, precision: int) -> float:
	if basis_amount <= 0:
		return 0.0
	return _quantize(amount * 100 / basis_amount, precision)


def _optional_rate(value, caster) -> float | None:
	if value in (None, ""):
		return None
	return caster(value)
