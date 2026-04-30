# fab HR Italy

Italian HR, payroll costing, and employee liability management for ERPNext.

## Scope

`fab_hr_italy` is the fab extension app for Italy-specific employee cost
management on top of ERPNext and HRMS.

Committed specifications live under `docs/specs`, including:

- `Phase 1 Scope`
- `Domain Model`
- `Decisions`

The app is intended to cover:

- payroll cost allocation for Italian reporting
- employer social contribution and yearly employer-cost analysis
- TFR accrual, reserve visibility, and settlement support
- employee advances and liability configuration needed for clean accounting
- company-level reporting for annual personnel cost and obligations

## Branches

- `develop`: integration branch for testing against Frappe/ERPNext `develop`
- `version-16`: stable branch for Frappe/ERPNext 16

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/fabricatorsltd/frappe-fab-hr-italy.git --branch version-16
bench --site [site] install-app fab_hr_italy
```

`fab_hr_italy` expects `erpnext`, `hrms`, and `fab` to already be present in
the bench.

## Contributing

Follow the official Frappe contribution guidelines:

- <https://github.com/frappe/erpnext/wiki/Contribution-Guidelines>

Use the upstream guidance for proposals, coding standards, pull requests, and
documentation updates when contributing to this app.

## Development

```bash
cd apps/fab_hr_italy
pre-commit install
```

Pre-commit is configured for Ruff, ESLint, Prettier, and PyUpgrade.

## License

GNU Affero General Public License v3.0
