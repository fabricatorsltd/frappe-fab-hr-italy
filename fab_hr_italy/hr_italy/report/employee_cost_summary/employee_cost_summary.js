frappe.query_reports["Employee Cost Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "from_month",
			label: __("From Month"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_month",
			label: __("To Month"),
			fieldtype: "Date",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "source_type",
			label: __("Source Type"),
			fieldtype: "Select",
			options: "\nManual",
		},
	],

	onload(report) {
		frappe
			.call({
				method: "fab_hr_italy.hr_italy.employee_cost_sources.get_employee_cost_source_config",
			})
			.then((r) => {
				const sources = (r.message?.sources || []).map((source) => source.value);
				const filter = report.get_filter("source_type");
				filter.df.options = ["", ...sources].join("\n");
				filter.refresh();
			});
	},
};
