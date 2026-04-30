# Domain Model

## Current phase

Phase 1 intentionally extends existing doctypes instead of introducing a new
Italian payroll document hierarchy.

## Company

`Company` carries the localization configuration:

- `fab_hri_enabled`
- `fab_hri_costing_basis`
- `fab_hri_employer_contribution_rate`
- `fab_hri_employer_insurance_rate`
- `fab_hri_tfr_rate`
- `fab_hri_post_company_cost_to_payroll_entry`
- expense and payable accounts for employer contribution, insurance, and TFR

Rationale: these values are company policy and chart-of-accounts setup, not
employee master data.

## Employee

`Employee` now carries optional payroll-rate overrides:

- `fab_hri_employee_section`
- `fab_hri_apply_employee_overrides`
- `fab_hri_employer_contribution_rate_override`
- `fab_hri_employer_insurance_rate_override`
- `fab_hri_tfr_rate_override`

Rationale: many Italian payroll obligations are shaped by employee-specific
conditions, but the first slice only needs rate overrides and should not create
another standalone doctype before that variability is proven.

## Salary Slip

`Salary Slip` stores the monthly computed outcome:

- `fab_hri_costing_basis_amount`
- `fab_hri_employer_contribution_amount`
- `fab_hri_employer_insurance_amount`
- `fab_hri_tfr_accrual_amount`
- `fab_hri_total_company_cost`

Rationale: the salary slip is the stable monthly payroll artifact already used
by payroll entry accounting and year-to-date analysis.

## Payroll Entry

`Payroll Entry` remains the accounting orchestrator. `fab_hr_italy` augments
its accrual journal logic by reading the persisted Salary Slip amounts and
posting additional expense and liability rows.

Rationale: employer-side costs must hit ERPNext accounting through the same
monthly payroll accounting flow to stay reconcilable.

## Future entities

Likely later-phase doctypes:

- Employee Fiscal Profile
- TFR Position / TFR Movement
- Italian Payroll Adjustment
- Yearly Personnel Cost Statement

These are deferred until the workflow requires entity-specific lifecycle and
audit behavior beyond what Company and Salary Slip already provide.