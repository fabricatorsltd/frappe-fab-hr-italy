app_name = "fab_hr_italy"
app_title = "HR Italy"
app_publisher = "fabricators"
app_description = "Italian HR, payroll costing, and employee liability management for ERPNext"
app_email = "support@fabricators.ltd"
app_license = "agpl-3.0"
app_home = "/app/fab-hr-italy"

# Apps
# ------------------

required_apps = ["erpnext", "hrms", "fab"]

add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"route": app_home,
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fab_hr_italy/css/fab_hr_italy.css"
# app_include_js = "/assets/fab_hr_italy/js/fab_hr_italy.js"

# include js, css files in header of web template
# web_include_css = "/assets/fab_hr_italy/css/fab_hr_italy.css"
# web_include_js = "/assets/fab_hr_italy/js/fab_hr_italy.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "fab_hr_italy/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

doctype_js = {
	"Company": "public/js/company.js",
	"Holiday List": "public/js/holiday_list.js",
}

fab_hr_italy_employee_cost_sources = [
	"fab_hr_italy.hr_italy.employee_cost_sources.get_core_employee_cost_sources"
]
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "fab_hr_italy/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "fab_hr_italy.utils.jinja_methods",
# 	"filters": "fab_hr_italy.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "fab_hr_italy.install.after_install"
after_migrate = "fab_hr_italy.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "fab_hr_italy.uninstall.before_uninstall"
# after_uninstall = "fab_hr_italy.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "fab_hr_italy.utils.before_app_install"
# after_app_install = "fab_hr_italy.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "fab_hr_italy.utils.before_app_uninstall"
# after_app_uninstall = "fab_hr_italy.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "fab_hr_italy.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fab_hr_italy.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Company": {
		"validate": "fab_hr_italy.company_setup.validate_company_cost_setup",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"fab_hr_italy.tasks.all"
# 	],
# 	"daily": [
# 		"fab_hr_italy.tasks.daily"
# 	],
# 	"hourly": [
# 		"fab_hr_italy.tasks.hourly"
# 	],
# 	"weekly": [
# 		"fab_hr_italy.tasks.weekly"
# 	],
# 	"monthly": [
# 		"fab_hr_italy.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "fab_hr_italy.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# override_doctype_class = {
# 	"Task": "fab_hr_italy.custom.task.CustomTaskMixin"
# }
override_doctype_class = {
	"Salary Slip": "fab_hr_italy.overrides.salary_slip.SalarySlip",
	"Payroll Entry": "fab_hr_italy.overrides.payroll_entry.PayrollEntry",
}

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "fab_hr_italy.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "fab_hr_italy.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["fab_hr_italy.utils.before_request"]
# after_request = ["fab_hr_italy.utils.after_request"]

# Job Events
# ----------
# before_job = ["fab_hr_italy.utils.before_job"]
# after_job = ["fab_hr_italy.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"fab_hr_italy.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
