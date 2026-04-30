# Decisions

## ADR-001: Extend HRMS instead of forking it

- Status: accepted
- Decision: use `override_doctype_class` for `Salary Slip` and `Payroll Entry`
  rather than copying HRMS doctypes into a parallel app.
- Rationale: payroll, employee benefits, loans, and journal orchestration are
  already implemented in HRMS. Forking them would increase divergence cost
  immediately.

## ADR-002: Start from gross pay as the costing basis

- Status: accepted for Phase 1
- Decision: compute employer contribution, insurance, and TFR from `gross_pay`.
- Rationale: it gives a deterministic first rule that uses an already computed
  HRMS amount and avoids prematurely encoding incomplete Italian component rules.
- Consequence: later phases may introduce employee- or component-specific bases
  without breaking the persisted field model.

## ADR-003: Persist monthly results on Salary Slip

- Status: accepted
- Decision: store computed amounts directly on `Salary Slip` custom fields.
- Rationale: downstream accounting, cash planning, and annual reporting need a
  stable monthly snapshot instead of recomputing from mutable settings.

## ADR-004: Payroll accrual posting is opt-in

- Status: accepted
- Decision: extra company-cost journal lines are posted only when the company
  enables the feature and provides the required accounts.
- Rationale: the app should support staged rollout where operators first review
  computed values before changing accounting behavior.

## ADR-005: Employee overrides extend but do not replace company policy

- Status: accepted
- Decision: salary-slip costing resolves from Company defaults first, then
  applies employee-specific rate overrides only when the employee explicitly
  enables them.
- Rationale: company configuration remains the deployment baseline, while
  employee overrides model the first unavoidable source of Italian payroll
  variability without fragmenting accounting policy.