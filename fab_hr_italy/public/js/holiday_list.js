function get_generate_button_label() {
	return __("Generate Italian Holidays");
}

function infer_holiday_year(frm) {
	const explicit_dates = [frm.doc.from_date, frm.doc.to_date].filter(Boolean);
	if (explicit_dates.length) {
		return explicit_dates[0].slice(0, 4);
	}

	const holiday_list_name = frm.doc.holiday_list_name || "";
	const year_match = holiday_list_name.match(/\b(19|20)\d{2}\b/);
	if (year_match) {
		return year_match[0];
	}

	return frappe.datetime.now_date().slice(0, 4);
}

async function ensure_holiday_date_range(frm) {
	if (frm.doc.from_date && frm.doc.to_date) {
		return;
	}

	const year = infer_holiday_year(frm);
	const from_date = frm.doc.from_date || `${year}-01-01`;
	const to_date = frm.doc.to_date || `${year}-12-31`;

	if (frm.doc.from_date !== from_date) {
		await frm.set_value("from_date", from_date);
	}

	if (frm.doc.to_date !== to_date) {
		await frm.set_value("to_date", to_date);
	}

	frappe.show_alert({
		message: __("Set holiday date range to {0}.", [
			`${frappe.datetime.str_to_user(from_date)} - ${frappe.datetime.str_to_user(to_date)}`,
		]),
		indicator: "blue",
	});
}

async function generate_italian_holidays(frm) {
	await ensure_holiday_date_range(frm);

	const response = await frappe.call({
		method: "fab_hr_italy.holiday_calendar.build_italian_holiday_rows",
		args: {
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date,
			weekly_off: frm.doc.weekly_off,
			is_half_day: frm.doc.is_half_day,
			existing_holiday_dates: (frm.doc.holidays || []).map((row) => row.holiday_date),
		},
		freeze: true,
		freeze_message: __("Generating Italian holidays..."),
	});

	const rows = response.message || [];
	for (const row of rows) {
		frm.add_child("holidays", row);
	}

	frm.refresh_field("holidays");
	frm.set_value("total_holidays", frm.doc.holidays.length);

	if (rows.length) {
		frappe.show_alert({
			message: __("Added {0} Italian holiday rows.", [rows.length]),
			indicator: "green",
		});
	} else {
		frappe.show_alert({
			message: __("No new Italian holidays were added."),
			indicator: "blue",
		});
	}
}

function refresh_generate_button(frm) {
	const button_label = get_generate_button_label();
	frm.remove_custom_button(button_label);
	frm.add_custom_button(button_label, () => generate_italian_holidays(frm));
}

frappe.ui.form.on("Holiday List", {
	refresh(frm) {
		refresh_generate_button(frm);
	},
	from_date(frm) {
		refresh_generate_button(frm);
	},
	to_date(frm) {
		refresh_generate_button(frm);
	},
});
