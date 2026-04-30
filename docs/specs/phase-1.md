# Phase 1 Scope

## Problem statement

`fab_hr_italy` must extend HRMS payroll and ERPNext accounting so Italian
employer-side payroll obligations become explicit operational and accounting
data. The first slice must avoid a fork of HRMS while making TFR accrual and
company-side cost visible on salary slips and optionally posting those amounts
into the payroll accrual journal entry.

## Scope

### In scope

- company-level configuration for Italian payroll costing
- monthly salary-slip computation of:
  - employer contribution amount
  - employer insurance amount
  - TFR accrual amount
  - total company cost
- payroll accrual journal augmentation with company-cost liability entries
- committed specs and rationale in-repo under `docs/specs`

### Out of scope

- full Italian tax withholding engine
- TFR liquidation and settlement workflow
- employee-specific INPS / INAIL segmentation rules
- year-end statutory reporting documents
- cash-planning dashboards and balance-sheet reporting UI

## Design principles

1. Reuse HRMS payroll as the execution engine.
2. Extend existing doctypes first; add new doctypes only when a workflow truly
   needs its own lifecycle.
3. Persist computed values on Salary Slip so downstream accounting and reporting
   read the same amounts.
4. Make accounting integration opt-in at company level.
5. Keep the first formula surface intentionally narrow and explicit.

## Acceptance criteria

Phase 1 is complete when:

1. A company can enable Italy HR payroll and configure rates plus accounts.
2. A salary slip computes and stores Italian company-cost amounts after normal
   HRMS payroll calculation.
3. A payroll accrual journal entry can include TFR and employer-side liabilities
   when the company opted into posting.
4. The implementation is covered by a narrow executable test for the costing
   formula and can be evolved without rewriting undocumented assumptions.

## Initial backlog

1. Add company and salary-slip custom fields.
2. Add pure costing service and tests.
3. Extend `Salary Slip` validation to compute persisted values.
4. Extend `Payroll Entry` accrual posting with company-cost entries.
5. Follow up with employee-level fiscal profile modeling.