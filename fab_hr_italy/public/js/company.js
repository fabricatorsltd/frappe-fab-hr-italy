const HR_COMPANY_ACCOUNT_FIELDS = [
	"fab_hri_gross_pay_expense_account",
	"fab_hri_employer_contribution_expense_account",
	"fab_hri_employer_contribution_payable_account",
	"fab_hri_employer_insurance_expense_account",
	"fab_hri_employer_insurance_payable_account",
	"fab_hri_tfr_expense_account",
	"fab_hri_tfr_payable_account",
];

const HISTORY_DEFAULT_TRAILING_MONTHS = 6;
const FORECAST_DEFAULT_MONTHS = 3;

function getMissingHrCompanyAccounts(doc) {
	return HR_COMPANY_ACCOUNT_FIELDS.filter((fieldname) => !doc[fieldname]);
}

function confirmProvisionHrAccounts() {
	return new Promise((resolve) => {
		frappe.confirm(
			__(
				"Italy HR payroll posting needs dedicated accounts. Create the missing accounts automatically now?"
			),
			() => resolve(true),
			() => resolve(false)
		);
	});
}

function formatMoney(value, currency) {
	if (typeof format_currency === "function") {
		return format_currency(value || 0, currency);
	}
	return `${Number(value || 0).toFixed(2)} ${currency || ""}`.trim();
}

function formatPercent(value) {
	return `${Number(value || 0).toFixed(2)}%`;
}

function formatSourceTypes(sourceTypes) {
	if (!sourceTypes?.length) {
		return __("Manual");
	}
	return sourceTypes.join(", ");
}

function renderHistorySummaryHtml(message) {
	return `
		<p>${__(
			"Applied weighted Italy HR payroll rates from {0} months of employee-cost history.",
			[message.month_count]
		)}</p>
		<table class="table table-bordered small">
			<tr>
				<th>${__("History Range")}</th>
				<td>${message.history_range_label || __("Not available")}</td>
				<th>${__("Sources Used")}</th>
				<td>${formatSourceTypes(message.source_types)}</td>
			</tr>
			<tr>
				<th>${__("Company Cost Basis")}</th>
				<td>${__(message.basis_mode || "Gross Pay")}</td>
				<th>${__("Average Monthly Headcount")}</th>
				<td>${Number(message.average_monthly_headcount || 0).toFixed(1)}</td>
			</tr>
			<tr>
				<th>${__("Employer Contribution Rate")}</th>
				<td>${formatPercent(message.employer_contribution_rate)}</td>
				<th>${__("Employer Insurance Rate")}</th>
				<td>${formatPercent(message.employer_insurance_rate)}</td>
			</tr>
			<tr>
				<th>${__("TFR Accrual Rate")}</th>
				<td>${formatPercent(message.tfr_rate)}</td>
				<th>${__("Average Monthly Total Company Cost")}</th>
				<td>${formatMoney(message.average_monthly_total_company_cost, message.currency)}</td>
			</tr>
		</table>
		<p class="text-muted">
			${__("Payroll accrual posting was left unchanged. Save the Company to persist these suggested rates.")}
		</p>
	`;
}

function renderForecastHtml(message) {
	return `
		<p>${__(
			"Estimated from the last {0} months of employee-cost history.",
			[message.month_count]
		)}</p>
		<table class="table table-bordered small">
			<tr>
				<th>${__("History Range")}</th>
				<td>${message.history_range_label || __("Not available")}</td>
				<th>${__("Sources Used")}</th>
				<td>${formatSourceTypes(message.source_types)}</td>
			</tr>
			<tr>
				<th>${__("Average Monthly Gross Pay")}</th>
				<td>${formatMoney(message.average_monthly_gross_monthly_amount, message.currency)}</td>
				<th>${__("Average Monthly Total Company Cost")}</th>
				<td>${formatMoney(message.average_monthly_total_company_cost, message.currency)}</td>
			</tr>
			<tr>
				<th>${__("Forecast Months")}</th>
				<td>${message.forecast.forecast_months}</td>
				<th>${__("Projected Total Company Cost")}</th>
				<td>${formatMoney(message.forecast.projected_total_company_cost, message.currency)}</td>
			</tr>
			<tr>
				<th>${__("Projected Gross Pay")}</th>
				<td>${formatMoney(message.forecast.projected_gross_monthly_amount, message.currency)}</td>
				<th>${__("Projected Employer Contributions")}</th>
				<td>${formatMoney(message.forecast.projected_employer_contribution_amount, message.currency)}</td>
			</tr>
			<tr>
				<th>${__("Projected Employer Insurance")}</th>
				<td>${formatMoney(message.forecast.projected_employer_insurance_amount, message.currency)}</td>
				<th>${__("Projected TFR Accrual")}</th>
				<td>${formatMoney(message.forecast.projected_tfr_accrual_amount, message.currency)}</td>
			</tr>
		</table>
	`;
}

function promptTrailingMonths(callback) {
	frappe.prompt(
		[
			{
				fieldname: "trailing_months",
				label: __("Trailing Months"),
				fieldtype: "Int",
				default: HISTORY_DEFAULT_TRAILING_MONTHS,
				reqd: 1,
			},
		],
		callback,
		__("Apply Cost Rates From History"),
		__("Apply")
	);
}

function promptForecastMonths(callback) {
	frappe.prompt(
		[
			{
				fieldname: "trailing_months",
				label: __("Trailing Months"),
				fieldtype: "Int",
				default: HISTORY_DEFAULT_TRAILING_MONTHS,
				reqd: 1,
			},
			{
				fieldname: "forecast_months",
				label: __("Forecast Months"),
				fieldtype: "Int",
				default: FORECAST_DEFAULT_MONTHS,
				reqd: 1,
			},
		],
		callback,
		__("Preview Employee Cost Forecast"),
		__("Preview")
	);
}

async function applyCostRatesFromHistory(frm, trailingMonths) {
	const response = await frappe.call({
		method: "fab_hr_italy.company_setup.get_company_cost_history_suggestion",
		args: {
			company: frm.doc.name,
			trailing_months: trailingMonths,
		},
		freeze: true,
		freeze_message: __("Analysing employee-cost history..."),
	});

	for (const [fieldname, value] of Object.entries(response.message.config_updates || {})) {
		await frm.set_value(fieldname, value);
	}

	frappe.msgprint({
		title: __("Company Cost History Applied"),
		indicator: "green",
		message: renderHistorySummaryHtml(response.message),
		wide: true,
	});
}

async function previewEmployeeCostForecast(frm, trailingMonths, forecastMonths) {
	const response = await frappe.call({
		method: "fab_hr_italy.company_setup.preview_employee_cost_forecast",
		args: {
			company: frm.doc.name,
			trailing_months: trailingMonths,
			forecast_months: forecastMonths,
		},
		freeze: true,
		freeze_message: __("Calculating employee-cost forecast..."),
	});

	frappe.msgprint({
		title: __("Employee Cost Forecast"),
		indicator: "blue",
		message: renderForecastHtml(response.message),
		wide: true,
	});
}

function addEmployeeCostHistoryButtons(frm) {
	if (!frm.doc.name || frm.is_new()) {
		return;
	}

	frm.add_custom_button(
		__("Apply Cost Rates From History"),
		() =>
			promptTrailingMonths((values) => applyCostRatesFromHistory(frm, values.trailing_months)),
		__("Italy HR Payroll")
	);
	frm.add_custom_button(
		__("Preview Employee Cost Forecast"),
		() =>
			promptForecastMonths((values) =>
				previewEmployeeCostForecast(frm, values.trailing_months, values.forecast_months)
			),
		__("Italy HR Payroll")
	);
}

const CONTRACT_TYPE_ACCOUNT_FIELDS = [
	"gross_pay_expense_account",
	"payroll_payable_account",
	"employer_contribution_expense_account",
	"employer_contribution_payable_account",
	"employer_insurance_expense_account",
	"employer_insurance_payable_account",
	"tfr_expense_account",
	"tfr_payable_account",
];

frappe.ui.form.on("Company", {
	setup(frm) {
		for (const fieldname of CONTRACT_TYPE_ACCOUNT_FIELDS) {
			frm.set_query(fieldname, "fab_hri_contract_type_accounts", () => ({
				filters: {
					company: frm.doc.name,
					is_group: 0,
					root_type: fieldname.endsWith("_expense_account") ? "Expense" : "Liability",
				},
			}));
		}
	},

	refresh(frm) {
		addEmployeeCostHistoryButtons(frm);
	},

	async before_save(frm) {
		if (!frm.doc.name || !frm.doc.fab_hri_post_company_cost_to_payroll_entry) {
			return;
		}

		if (!getMissingHrCompanyAccounts(frm.doc).length) {
			return;
		}

		const shouldProvision = await confirmProvisionHrAccounts();
		if (!shouldProvision) {
			frappe.throw(
				__("Create or select the missing Italy HR accounts before saving with payroll-entry posting enabled.")
			);
		}

		const response = await frappe.call({
			method: "fab_hr_italy.company_setup.provision_company_cost_setup",
			args: { company: frm.doc.name },
			freeze: true,
			freeze_message: __("Creating Italy HR accounts..."),
		});

		for (const [fieldname, value] of Object.entries(response.message.updates || {})) {
			frm.doc[fieldname] = value;
		}

		if (response.message.message) {
			frappe.show_alert({ message: response.message.message, indicator: "green" });
		}
	},
});
