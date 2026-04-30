# Employee Overrides

## Problem statement

Company-wide Italian payroll costing is not enough for production use because
some employer-side rates vary by employee profile. The next slice must allow
employee-specific overrides while keeping Company as the default source of
policy and accounting setup.

## Scope

### In scope

- optional employee-level override switch
- employee-level override rates for:
  - employer contribution
  - employer insurance
  - TFR accrual
- company fallback when overrides are not enabled or not filled

### Out of scope

- employee-specific accounting accounts
- automatic determination from contract type or classification
- standalone employee fiscal profile doctype

## Resolution rules

1. Load the Company costing configuration.
2. If the employee did not enable overrides, use Company values unchanged.
3. If the employee enabled overrides, replace each rate only when the employee
   field has a value.
4. Keep Company enablement and accounting accounts authoritative.

## Acceptance criteria

1. Employee override fields exist and are translatable.
2. Salary-slip costing uses employee rates when enabled.
3. Missing employee override values fall back to Company values.
4. The fallback behavior is covered by a focused executable test.