const HRMS_MANAGED_FIELDS = [
	"company",
	"employee_name",
	"employee_identifier",
	"workplace",
	"job_title",
	"department_name",
	"contract_kind",
	"contract_start_date",
	"contract_end_date",
];

function get_file_sources(frm) {
	const config = frm.employee_cost_source_config || { sources: [] };
	return (config.sources || []).filter((source) => source.entry_mode === "file");
}

function format_source_options(sources) {
	return ["", ...sources.map((source) => source.value)].join("\n");
}

function apply_source_config(frm, config) {
	const sources = config.sources || [];
	const valid_values = sources.map((source) => source.value);

	frm.employee_cost_source_config = config;
	frm.employee_cost_source_lookup = Object.fromEntries(
		sources.map((source) => [source.value, source])
	);
	frm.set_df_property("source_type", "options", format_source_options(sources));

	if (!valid_values.includes(frm.doc.source_type)) {
		frm.set_value("source_type", valid_values[0] || "");
	}
}

function open_source_import_uploader(frm, source) {
	if (!source?.upload_method) {
		frappe.msgprint(
			__(
				"The {0} origin is provided by an import app and must expose an upload handler.",
				[source.label || source.value]
			)
		);
		return;
	}

	new frappe.ui.FileUploader({
		method: source.upload_method,
		allow_toggle_private: false,
		allow_take_photo: false,
		restrictions: source.allowed_file_types
			? { allowed_file_types: source.allowed_file_types }
			: undefined,
		on_success(_file_doc, r) {
			const result = r.message || {};

			if (result.message) {
				frappe.msgprint(result.message);
			}

			if (result.route) {
				frappe.set_route(result.route);
				return;
			}

			if (result.doctype && result.name) {
				frappe.set_route("Form", result.doctype, result.name);
				return;
			}

			frm.reload_doc();
		},
	});
}

function prompt_source_import(frm, source) {
	if (!source || source.entry_mode !== "file" || !frm.is_new()) {
		return;
	}

	if (frm._prompted_source_import === source.value) {
		return;
	}

	frm._prompted_source_import = source.value;

	frappe.msgprint({
		title: __("Import from File"),
		message: __(
			"The {0} origin imports multiple rows from a file instead of filling a single employee entry manually.",
			[source.label || source.value]
		),
		primary_action: {
			label: source.upload_label || __("Upload File"),
			action: () => open_source_import_uploader(frm, source),
		},
	});
}

function add_file_import_button(frm) {
	if (frm._added_file_import_button) {
		return;
	}

	const file_sources = get_file_sources(frm);
	if (!file_sources.length) {
		return;
	}

	frm._added_file_import_button = true;
	frm.add_custom_button(__("Import from File"), () => {
		if (file_sources.length === 1) {
			open_source_import_uploader(frm, file_sources[0]);
			return;
		}

		const options = file_sources.map((source) => ({
			label: source.label || source.value,
			value: source.value,
		}));
		const dialog = new frappe.ui.Dialog({
			title: __("Select Import Source"),
			fields: [
				{
					fieldname: "source_type",
					fieldtype: "Select",
					label: __("Source Type"),
					options: options.map((option) => option.value).join("\n"),
					default: options[0]?.value,
					reqd: 1,
				},
			],
			primary_action_label: __("Upload File"),
			primary_action(values) {
				const source = file_sources.find((item) => item.value === values.source_type);
				dialog.hide();
				open_source_import_uploader(frm, source);
			},
		});
		dialog.show();
	});
}

function add_accounting_buttons(frm) {
	if (!frm.doc.name || frm.is_new()) {
		return;
	}

	if (frm.doc.accrual_journal_entry) {
		frm.add_custom_button(__("Open Accrual Journal Entry"), () => {
			frappe.set_route("Form", "Journal Entry", frm.doc.accrual_journal_entry);
		});
	}

	frm.add_custom_button(__("Post Month to GL"), async () => {
		const response = await frappe.call({
			method: "fab_hr_italy.employee_cost_accounting.post_employee_cost_month_to_gl",
			args: {
				employee_cost_entry: frm.doc.name,
			},
			freeze: true,
			freeze_message: __("Posting employee cost to GL..."),
		});

		if (response.message?.message) {
			frappe.show_alert({ message: response.message.message, indicator: "green" });
		}

		if (response.message?.route) {
			await frm.reload_doc();
			return;
		}
		await frm.reload_doc();
	});
}

function load_source_config(frm) {
	return frappe
		.call({
			method: "fab_hr_italy.hr_italy.employee_cost_sources.get_employee_cost_source_config",
		})
		.then((r) => {
			const config = r.message || { sources: [] };
			apply_source_config(frm, config);
			add_file_import_button(frm);

			if (frm.doc.source_type) {
				prompt_source_import(frm, frm.employee_cost_source_lookup?.[frm.doc.source_type]);
			}
		});
}

function toggle_hrms_managed_fields(frm) {
	const readOnly = Boolean(frm.doc.employee);

	for (const fieldname of HRMS_MANAGED_FIELDS) {
		frm.set_df_property(fieldname, "read_only", readOnly ? 1 : 0);
	}
}

function sync_employee_defaults(frm) {
	if (!frm.doc.employee) {
		toggle_hrms_managed_fields(frm);
		return;
	}

	frappe.db
		.get_value("Employee", frm.doc.employee, [
			"company",
			"employee_name",
			"employee_number",
			"branch",
			"designation",
			"department",
			"employment_type",
			"date_of_joining",
			"contract_end_date",
		])
		.then(({ message }) => {
			if (!message) {
				return;
			}

			frm.set_value({
				company: message.company || frm.doc.company,
				employee_name: message.employee_name || frm.doc.employee_name,
				employee_identifier: message.employee_number || frm.doc.employee,
				workplace: message.branch || null,
				job_title: message.designation || null,
				department_name: message.department || null,
				contract_kind: message.employment_type || null,
				contract_start_date: message.date_of_joining || null,
				contract_end_date: message.contract_end_date || null,
			});
			toggle_hrms_managed_fields(frm);
		});
}

frappe.ui.form.on("Employee Cost Entry", {
	setup(frm) {
		frm.set_query("employee", () => {
			const filters = { status: "Active" };

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			return { filters };
		});

		load_source_config(frm);
	},

	refresh(frm) {
		toggle_hrms_managed_fields(frm);
		add_file_import_button(frm);
		add_accounting_buttons(frm);
	},

	employee(frm) {
		sync_employee_defaults(frm);
	},

	source_type(frm) {
		prompt_source_import(frm, frm.employee_cost_source_lookup?.[frm.doc.source_type]);
	},
});
