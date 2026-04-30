from __future__ import annotations

from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip as HRMSSalarySlip

from fab_hr_italy.company_costing import CompanyCostBreakdown, compute_company_cost_breakdown, get_company_cost_config


class SalarySlip(HRMSSalarySlip):
	def validate(self):
		super().validate()
		self.apply_italian_company_costing()

	def apply_italian_company_costing(self):
		config = get_company_cost_config(self.company, self.employee)
		precision = self.precision("fab_hri_total_company_cost") or 2

		if config.enabled and config.basis_mode == "Gross Pay":
			breakdown = compute_company_cost_breakdown(self.gross_pay or 0, config, precision=precision)
		else:
			breakdown = CompanyCostBreakdown()

		self.fab_hri_costing_basis_amount = breakdown.basis_amount
		self.fab_hri_employer_contribution_amount = breakdown.employer_contribution_amount
		self.fab_hri_employer_insurance_amount = breakdown.employer_insurance_amount
		self.fab_hri_tfr_accrual_amount = breakdown.tfr_accrual_amount
		self.fab_hri_total_company_cost = breakdown.total_company_cost