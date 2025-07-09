# -*- coding: utf-8 -*-
# Fichier: ovh_sms_integration/hooks.py
# Hooks pour intégrer les campagnes SMS dans ERPNext

app_name = "ovh_sms_integration"
app_title = "OVH SMS Integration"
app_publisher = "Mohamed Kachtit"
app_description = "Intégration SMS OVH pour ERPNext avec campagnes de tarification"
app_email = "mokachtit@gmail.com"
app_license = "MIT"

# Apps
# ------------------

# Inclusions dans l'interface
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/ovh_sms_integration/css/sms_campaigns.css"
app_include_js = "/assets/ovh_sms_integration/js/sms_campaigns.js"

# Icônes SVG
# ------------------
app_include_icons = "ovh_sms_integration/public/icons.svg"

# Installation
# ------------
after_install = "ovh_sms_integration.install.after_install"

# Événements de documents
# ---------------
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
		"validate": "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.validate_campaign_hook",
		"on_submit": "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.on_campaign_submit_hook",
		"before_save": "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.calculate_totals_hook"
	}
}

# Tâches planifiées
# ---------------
scheduler_events = {
	"all": [
		"ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.process_event_reminders"
	],
	"hourly": [
		"ovh_sms_integration.tasks.check_event_reminders_hourly",
		"ovh_sms_integration.tasks.process_scheduled_campaigns"
	],
	"daily": [
		"ovh_sms_integration.tasks.reset_daily_counters",
		"ovh_sms_integration.tasks.cleanup_old_reminder_logs",
		"ovh_sms_integration.tasks.send_daily_campaign_report"
	],
	"weekly": [
		"ovh_sms_integration.tasks.send_weekly_reminder_report",
		"ovh_sms_integration.tasks.cleanup_old_campaigns"
	]
}

# Permissions personnalisées
# ------------------------------
permission_query_conditions = {
	"SMS Pricing Campaign": "ovh_sms_integration.permissions.get_campaign_permission_query_conditions",
}

has_permission = {
	"SMS Pricing Campaign": "ovh_sms_integration.permissions.has_campaign_permission",
}

# Surcharge de méthodes
# ------------------------------
override_whitelisted_methods = {
	"frappe.desk.form.save.savedocs": "ovh_sms_integration.utils.campaign_utils.enhanced_save_campaign"
}

# Configuration du tableau de bord
# ------------------------------
override_doctype_dashboards = {
	"Customer": "ovh_sms_integration.dashboard.get_customer_dashboard_data",
	"Item": "ovh_sms_integration.dashboard.get_item_dashboard_data"
}

# Configuration Jinja
# ----------
jinja = {
	"methods": [
		"ovh_sms_integration.utils.template_utils.format_sms_message",
		"ovh_sms_integration.utils.template_utils.get_customer_mobile",
		"ovh_sms_integration.utils.template_utils.format_currency_local"
	],
	"filters": [
		"ovh_sms_integration.utils.template_utils.phone_format",
		"ovh_sms_integration.utils.template_utils.sms_preview"
	]
}

# Liens rapides dans la barre latérale
# ------------------
standard_portal_menu_items = [
	{"title": _("SMS Campaigns"), "route": "/sms-campaigns", "reference_doctype": "SMS Pricing Campaign"}
]

# Configuration des notifications
# ------------------
notification_config = "ovh_sms_integration.notifications.get_notification_config"

# Configuration de l'exportation de données
# --------------------
data_import_tool = [
	{
		"module_name": "OVH SMS Integration",
		"doctype": "SMS Pricing Campaign",
		"allow_import": 1,
		"template_options": {
			"with_data": 1,
			"file_type": "CSV"
		}
	}
]

# Fixtures pour l'installation
# -----------------------------
fixtures = [
	{
		"doctype": "Role",
		"filters": [
			["name", "in", ["SMS Manager", "SMS User", "Campaign Manager"]]
		]
	},
	{
		"doctype": "Custom Field",
		"filters": [
			["dt", "in", ["Customer", "Item", "Sales Order"]]
		]
	}
]

# Configuration du workspace (bureau)
# ------------------------------------
workspace = {
	"SMS Campaigns": {
		"icon": "fa fa-mobile",
		"color": "#3498db",
		"shortcuts": [
			{
				"type": "DocType",
				"name": "SMS Pricing Campaign",
				"color": "#3498db"
			},
			{
				"type": "DocType", 
				"name": "OVH SMS Settings",
				"color": "#e74c3c"
			},
			{
				"type": "DocType",
				"name": "SMS Event Reminder", 
				"color": "#f39c12"
			}
		],
		"charts": [
			{
				"chart_name": "SMS Campaign Performance",
				"label": "Performance des Campagnes SMS"
			}
		]
	}
}

# Hooks pour les websites/portails
# ------------------
website_route_rules = [
	{"from_route": "/sms-campaigns/<path:name>", "to_route": "sms_campaigns"},
]

# Configuration de l'API
# ----------------------
override_api_methods = {
	"ovh_sms_integration.api.v1.campaigns.get_campaigns": "GET",
	"ovh_sms_integration.api.v1.campaigns.create_campaign": "POST",
	"ovh_sms_integration.api.v1.campaigns.send_campaign": "POST"
}

# Configuration des rapports
# ---------------------------
standard_reports = [
	{
		"module": "OVH SMS Integration",
		"title": "SMS Campaign Analysis",
		"doctype": "SMS Pricing Campaign",
		"is_standard": "Yes"
	}
]

# Configuration mobile/responsive
# -------------------------------
mobile_responsive = 1

# Configuration PWA (Progressive Web App)
# ----------------------------------------
pwa_icon = "/assets/ovh_sms_integration/images/sms_icon.png"
pwa_short_name = "SMS Campaigns"

# Boot info pour le client
# -------------------------
boot_session = "ovh_sms_integration.boot.get_bootinfo"

# Configuration d'internationalisation
# ------------------------------------
default_language = "fr"
languages = ["en", "fr", "es"]

# Configuration des emails
# -------------------------
email_brand_image = "/assets/ovh_sms_integration/images/logo.png"

# Configuration de logging personnalisé
# -------------------------------------
log_clearance = {
	"SMS Campaign Log": 30,  # Garder 30 jours
	"SMS Send Log": 7,       # Garder 7 jours
	"SMS Error Log": 90      # Garder 90 jours
}

# Configuration des tests
# -----------------------
before_tests = "ovh_sms_integration.tests.setup_test_data"

# Configuration de la base de données
# -----------------------------------
on_session_creation = "ovh_sms_integration.session.setup_user_sms_preferences"

# Configuration avancée pour l'intégration
# -----------------------------------------

# Auto-création de champs personnalisés
setup_custom_fields = {
	"Customer": [
		{
			"fieldname": "sms_opt_out",
			"label": "Opt-out SMS",
			"fieldtype": "Check",
			"insert_after": "mobile_no",
			"description": "Client ne souhaite pas recevoir de SMS marketing"
		},
		{
			"fieldname": "preferred_sms_time",
			"label": "Horaire préféré SMS",
			"fieldtype": "Time",
			"insert_after": "sms_opt_out",
			"description": "Heure préférée pour recevoir des SMS"
		},
		{
			"fieldname": "sms_language",
			"label": "Langue SMS",
			"fieldtype": "Select",
			"options": "Français\nEnglish\nEspañol",
			"default": "Français",
			"insert_after": "preferred_sms_time"
		}
	],
	"Item": [
		{
			"fieldname": "sms_description",
			"label": "Description SMS",
			"fieldtype": "Data",
			"insert_after": "description",
			"description": "Description courte pour les SMS (max 50 caractères)"
		},
		{
			"fieldname": "sms_promo_eligible",
			"label": "Éligible promo SMS",
			"fieldtype": "Check",
			"insert_after": "sms_description",
			"description": "Article peut être inclus dans les campagnes SMS"
		}
	],
	"Sales Order": [
		{
			"fieldname": "sms_sent",
			"label": "SMS envoyé",
			"fieldtype": "Check",
			"insert_after": "status",
			"read_only": 1,
			"description": "SMS de confirmation envoyé au client"
		},
		{
			"fieldname": "sms_sent_time",
			"label": "Heure envoi SMS",
			"fieldtype": "Datetime",
			"insert_after": "sms_sent",
			"read_only": 1
		}
	]
}

# Configuration des workflows
# ---------------------------
workflow_state_field = {
	"SMS Pricing Campaign": "workflow_state"
}

# Configuration de la recherche globale
# -------------------------------------
global_search_doctypes = {
	"SMS Pricing Campaign": ["title", "status"],
}

# Configuration du cache
# ----------------------
cache_withmongo = 0
cache_redis_server = "redis://localhost:6379"

# Configuration des webhooks
# ---------------------------
webhook_events = {
	"SMS Pricing Campaign": {
		"on_submit": "ovh_sms_integration.webhooks.campaign_submitted",
		"on_cancel": "ovh_sms_integration.webhooks.campaign_cancelled"
	}
}

# Configuration de la sécurité
# -----------------------------
ignore_links_on_delete = ["SMS Campaign Log", "SMS Send Log"]

# Configuration des domaines (multi-tenant)
# ------------------------------------------
domains = {
	"SMS Marketing": {
		"modules": ["OVH SMS Integration"],
		"doctypes": ["SMS Pricing Campaign", "SMS Pricing Item"]
	}
}

# Configuration de l'impression
# ------------------------------
print_style = "ovh_sms_integration/templates/print_formats/campaign_print.css"

# Configuration des graphiques
# -----------------------------
dashboard_charts = [
	{
		"chart_name": "SMS Campaign ROI",
		"chart_type": "line",
		"doctype": "SMS Pricing Campaign",
		"based_on": "campaign_date",
		"value_based_on": "profit_potential"
	},
	{
		"chart_name": "SMS Success Rate",
		"chart_type": "percentage",
		"doctype": "SMS Pricing Campaign", 
		"based_on": "status"
	}
]

# Configuration des événements système
# ------------------------------------
on_app_install = "ovh_sms_integration.install.setup_default_sms_templates"
on_app_uninstall = "ovh_sms_integration.uninstall.cleanup_sms_data"

# Configuration de l'intégration e-commerce
# -----------------------------------------
shopping_cart_settings = {
	"enable_sms_notifications": 1,
	"sms_on_cart_update": 0,
	"sms_on_checkout": 1
}

# Configuration des tâches d'arrière-plan
# ---------------------------------------
background_jobs = {
	"process_bulk_sms": {
		"method": "ovh_sms_integration.tasks.process_bulk_sms_queue",
		"queue": "long"
	},
	"generate_campaign_report": {
		"method": "ovh_sms_integration.reports.generate_campaign_analytics",
		"queue": "short"
	}
}

# Configuration de l'audit et logs
# --------------------------------
audit_trail = {
	"SMS Pricing Campaign": {
		"log_changes": 1,
		"log_deletes": 1,
		"retention_days": 365
	}
}

# Configuration des intégrations tierces
# --------------------------------------
third_party_integrations = {
	"zapier": {
		"enabled": 1,
		"webhook_url": "/api/method/ovh_sms_integration.integrations.zapier_webhook"
	},
	"whatsapp": {
		"enabled": 0,
		"fallback_to_sms": 1
	}
}

# Configuration des KPI et métriques
# ----------------------------------
metrics_config = {
	"sms_delivery_rate": {
		"calculation": "success_count / total_sent * 100",
		"target": 95,
		"alert_threshold": 90
	},
	"campaign_roi": {
		"calculation": "(revenue - cost) / cost * 100", 
		"target": 200,
		"alert_threshold": 100
	}
}

# Configuration de l'IA et automatisation
# ---------------------------------------
ai_features = {
	"smart_send_time": {
		"enabled": 1,
		"model": "customer_behavior_prediction"
	},
	"message_optimization": {
		"enabled": 1,
		"a_b_testing": 1
	}
}

# Configuration de conformité RGPD
# --------------------------------
gdpr_settings = {
	"data_retention_days": 1095,  # 3 ans
	"anonymize_after_days": 2190,  # 6 ans
	"consent_tracking": 1,
	"right_to_be_forgotten": 1
}

# Configuration de monitoring et alertes
# --------------------------------------
monitoring = {
	"sms_quota_alerts": {
		"warning_threshold": 80,
		"critical_threshold": 95,
		"notification_emails": ["admin@domain.com"]
	},
	"failed_campaigns": {
		"alert_after_failures": 3,
		"auto_pause_campaign": 1
	}
}