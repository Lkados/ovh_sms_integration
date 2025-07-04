app_name = "ovh_sms_integration"
app_title = "Ovh Sms Integration"
app_publisher = "Mohamed Kachtit"
app_description = "Ovh sms intergration for erpNext"
app_email = "mokachtit@gmail.colm"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ovh_sms_integration",
# 		"logo": "/assets/ovh_sms_integration/logo.png",
# 		"title": "Ovh Sms Integration",
# 		"route": "/ovh_sms_integration",
# 		"has_permission": "ovh_sms_integration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ovh_sms_integration/css/ovh_sms_integration.css"
# app_include_js = "/assets/ovh_sms_integration/js/ovh_sms_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/ovh_sms_integration/css/ovh_sms_integration.css"
# web_include_js = "/assets/ovh_sms_integration/js/ovh_sms_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ovh_sms_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ovh_sms_integration/public/icons.svg"

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

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ovh_sms_integration.utils.jinja_methods",
# 	"filters": "ovh_sms_integration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ovh_sms_integration.install.before_install"
after_install = "ovh_sms_integration.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ovh_sms_integration.uninstall.before_uninstall"
# after_uninstall = "ovh_sms_integration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ovh_sms_integration.utils.before_app_install"
# after_app_install = "ovh_sms_integration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ovh_sms_integration.utils.before_app_uninstall"
# after_app_uninstall = "ovh_sms_integration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ovh_sms_integration.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Order": {
		"on_submit": "ovh_sms_integration.utils.sms_utils.send_sales_order_sms"
	},
	"Payment Entry": {
		"on_submit": "ovh_sms_integration.utils.sms_utils.send_payment_confirmation_sms"
	},
	"Delivery Note": {
		"on_submit": "ovh_sms_integration.utils.sms_utils.send_delivery_sms"
	},
	"Purchase Order": {
		"on_submit": "ovh_sms_integration.utils.sms_utils.send_purchase_order_sms"
	},
	"SMS Pricing Campaign": {
		"validate": "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.validate_campaign",
		"on_submit": "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.on_campaign_submit"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.process_event_reminders"
	],
	"hourly": [
		"ovh_sms_integration.tasks.check_event_reminders_hourly"
	],
	"daily": [
		"ovh_sms_integration.tasks.reset_daily_counters",
		"ovh_sms_integration.tasks.cleanup_old_reminder_logs"
	],
	"weekly": [
		"ovh_sms_integration.tasks.send_weekly_reminder_report"
	]
}

# Testing
# -------

# before_tests = "ovh_sms_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ovh_sms_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ovh_sms_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ovh_sms_integration.utils.before_request"]
# after_request = ["ovh_sms_integration.utils.after_request"]

# Job Events
# ----------
# before_job = ["ovh_sms_integration.utils.before_job"]
# after_job = ["ovh_sms_integration.utils.after_job"]

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
# 	"ovh_sms_integration.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Event Reminder Hooks
# ---------------------

# SMS Event Reminder settings
event_reminder_settings = {
	"check_interval_minutes": 30,  # Vérifier toutes les 30 minutes
	"max_reminders_per_run": 100,  # Limite de rappels par exécution
	"retry_failed_after_hours": 2,  # Réessayer les échecs après 2h
	"cleanup_logs_after_days": 30   # Nettoyer les logs après 30 jours
}

# Fixtures pour l'installation
# -----------------------------
fixtures = [
	{
		"doctype": "Custom Role",
		"filters": [
			["name", "in", ["SMS Manager", "SMS User"]]
		]
	}
]