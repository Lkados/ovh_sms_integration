# -*- coding: utf-8 -*-
# Fichier: ovh_sms_integration/permissions.py
# Gestion des permissions pour les campagnes SMS

from __future__ import unicode_literals
import frappe
from frappe import _

def get_campaign_permission_query_conditions(user=None):
	"""Conditions de permission pour les campagnes SMS"""
	if not user:
		user = frappe.session.user
	
	# Super utilisateurs voient tout
	if "System Manager" in frappe.get_roles(user):
		return ""
	
	# Gestionnaires SMS voient toutes les campagnes de leur société
	if "SMS Manager" in frappe.get_roles(user):
		user_company = frappe.db.get_value("User", user, "company")
		if user_company:
			return f"(`tabSMS Pricing Campaign`.company = '{user_company}' or `tabSMS Pricing Campaign`.company is null)"
		else:
			return ""
	
	# Utilisateurs SMS voient seulement leurs campagnes
	if "SMS User" in frappe.get_roles(user):
		return f"`tabSMS Pricing Campaign`.owner = '{user}'"
	
	# Autres utilisateurs : aucun accès
	return "1=0"

def has_campaign_permission(doc, user=None):
	"""Vérifie si l'utilisateur a les permissions sur une campagne"""
	if not user:
		user = frappe.session.user
	
	# Super utilisateurs
	if "System Manager" in frappe.get_roles(user):
		return True
	
	# Gestionnaires SMS
	if "SMS Manager" in frappe.get_roles(user):
		user_company = frappe.db.get_value("User", user, "company")
		if user_company and doc.company == user_company:
			return True
		if not doc.company:  # Campagnes sans société
			return True
	
	# Utilisateurs SMS - leurs propres campagnes
	if "SMS User" in frappe.get_roles(user):
		return doc.owner == user
	
	return False

def validate_sms_permissions(doc, method):
	"""Validation des permissions lors de la sauvegarde"""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	
	if not has_campaign_permission(doc):
		frappe.throw(_("Permissions insuffisantes pour cette campagne"))

def validate_sms_sending_permission(user=None):
	"""Vérifie les permissions d'envoi de SMS"""
	if not user:
		user = frappe.session.user
	
	required_roles = ["SMS Manager", "SMS User", "System Manager"]
	user_roles = frappe.get_roles(user)
	
	if not any(role in user_roles for role in required_roles):
		frappe.throw(_("Permission d'envoi SMS requise"))
	
	# Vérification des quotas utilisateur
	check_user_sms_quota(user)

def check_user_sms_quota(user):
	"""Vérifie le quota SMS de l'utilisateur"""
	try:
		# Récupérer les paramètres de quota
		user_doc = frappe.get_doc("User", user)
		
		# Quota par défaut par rôle
		role_quotas = {
			"SMS User": 100,    # 100 SMS par jour
			"SMS Manager": 500, # 500 SMS par jour
			"System Manager": 9999  # Illimité
		}
		
		user_roles = frappe.get_roles(user)
		max_quota = 0
		
		for role in user_roles:
			if role in role_quotas:
				max_quota = max(max_quota, role_quotas[role])
		
		if max_quota == 0:
			frappe.throw(_("Aucun quota SMS défini pour cet utilisateur"))
		
		# Compter les SMS envoyés aujourd'hui
		from datetime import datetime, timedelta
		today = datetime.now().date()
		
		sent_today = frappe.db.count("SMS Campaign Log", {
			"sender": user,
			"date": today,
			"status": "Sent"
		})
		
		if sent_today >= max_quota:
			frappe.throw(_("Quota SMS journalier atteint ({0}/{1})").format(sent_today, max_quota))
		
		return max_quota - sent_today
		
	except Exception as e:
		frappe.log_error(f"Erreur vérification quota SMS: {e}")
		return 0

@frappe.whitelist()
def get_user_sms_quota():
	"""API pour récupérer le quota SMS utilisateur"""
	try:
		remaining = check_user_sms_quota(frappe.session.user)
		return {
			"success": True,
			"remaining_quota": remaining
		}
	except Exception as e:
		return {
			"success": False,
			"message": str(e)
		}

def setup_campaign_security():
	"""Configure la sécurité des campagnes SMS"""
	# Création des rôles si ils n'existent pas
	create_sms_roles()
	
	# Configuration des permissions par défaut
	setup_default_permissions()
	
	# Configuration des limites de sécurité
	setup_security_limits()

def create_sms_roles():
	"""Crée les rôles SMS nécessaires"""
	roles_to_create = [
		{
			'role_name': 'Campaign Manager',
			'desk_access': 1,
			'description': 'Peut créer et gérer les campagnes SMS de marketing'
		},
		{
			'role_name': 'SMS Operator',
			'desk_access': 1,
			'description': 'Peut exécuter les campagnes SMS mais pas les modifier'
		},
		{
			'role_name': 'SMS Viewer',
			'desk_access': 1,
			'description': 'Peut consulter les rapports SMS en lecture seule'
		}
	]
	
	for role_data in roles_to_create:
		if not frappe.db.exists('Role', role_data['role_name']):
			role_doc = frappe.get_doc({
				'doctype': 'Role',
				'role_name': role_data['role_name'],
				'desk_access': role_data['desk_access'],
				'description': role_data['description']
			})
			role_doc.insert()
			frappe.logger().info(f"Rôle créé: {role_data['role_name']}")

def setup_default_permissions():
	"""Configure les permissions par défaut pour les campagnes"""
	permissions_config = {
		'SMS Pricing Campaign': [
			{'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1, 'submit': 1},
			{'role': 'SMS Manager', 'read': 1, 'write': 1, 'create': 1, 'submit': 1},
			{'role': 'Campaign Manager', 'read': 1, 'write': 1, 'create': 1, 'submit': 1},
			{'role': 'SMS User', 'read': 1, 'write': 1, 'create': 1},
			{'role': 'SMS Operator', 'read': 1, 'submit': 1},
			{'role': 'SMS Viewer', 'read': 1}
		],
		'SMS Pricing Item': [
			{'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1},
			{'role': 'SMS Manager', 'read': 1, 'write': 1, 'create': 1},
			{'role': 'Campaign Manager', 'read': 1, 'write': 1, 'create': 1},
			{'role': 'SMS User', 'read': 1, 'write': 1, 'create': 1},
			{'role': 'SMS Viewer', 'read': 1}
		]
	}
	
	for doctype, perms in permissions_config.items():
		setup_doctype_permissions(doctype, perms)

def setup_doctype_permissions(doctype, permissions):
	"""Configure les permissions pour un DocType spécifique"""
	try:
		for perm in permissions:
			# Vérifier si la permission existe déjà
			existing = frappe.db.exists('DocPerm', {
				'parent': doctype,
				'role': perm['role']
			})
			
			if not existing:
				perm_doc = frappe.get_doc({
					'doctype': 'DocPerm',
					'parent': doctype,
					'parenttype': 'DocType',
					'parentfield': 'permissions',
					'role': perm['role'],
					'read': perm.get('read', 0),
					'write': perm.get('write', 0),
					'create': perm.get('create', 0),
					'delete': perm.get('delete', 0),
					'submit': perm.get('submit', 0),
					'cancel': perm.get('cancel', 0),
					'amend': perm.get('amend', 0)
				})
				perm_doc.insert()
				frappe.logger().info(f"Permission créée: {doctype} - {perm['role']}")
		
	except Exception as e:
		frappe.log_error(f"Erreur setup permissions {doctype}: {e}")

def setup_security_limits():
	"""Configure les limites de sécurité"""
	security_settings = {
		'max_sms_per_campaign': 10000,
		'max_campaigns_per_user_per_day': 5,
		'max_concurrent_campaigns': 3,
		'require_approval_above_amount': 5000,
		'require_approval_above_sms_count': 1000
	}
	
	# Sauvegarder dans les paramètres système
	for key, value in security_settings.items():
		frappe.db.set_value("System Settings", "System Settings", f"sms_{key}", value)

def validate_campaign_limits(doc, method):
	"""Valide les limites de sécurité pour une campagne"""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	
	# Limite sur le nombre de SMS
	max_sms = frappe.db.get_single_value("System Settings", "sms_max_sms_per_campaign") or 10000
	if doc.total_customers > max_sms:
		frappe.throw(_("Limite dépassée: maximum {0} SMS par campagne").format(max_sms))
	
	# Limite sur le montant
	max_amount = frappe.db.get_single_value("System Settings", "sms_require_approval_above_amount") or 5000
	if doc.estimated_revenue > max_amount:
		doc.requires_approval = 1
	
	# Limite sur le nombre de SMS nécessitant approbation
	max_sms_approval = frappe.db.get_single_value("System Settings", "sms_require_approval_above_sms_count") or 1000
	if doc.total_customers > max_sms_approval:
		doc.requires_approval = 1

def check_concurrent_campaigns(user=None):
	"""Vérifie le nombre de campagnes simultanées"""
	if not user:
		user = frappe.session.user
	
	max_concurrent = frappe.db.get_single_value("System Settings", "sms_max_concurrent_campaigns") or 3
	
	active_campaigns = frappe.db.count("SMS Pricing Campaign", {
		"owner": user,
		"status": ["in", ["Prêt", "En cours"]],
		"docstatus": 1
	})
	
	if active_campaigns >= max_concurrent:
		frappe.throw(_("Limite atteinte: maximum {0} campagnes simultanées").format(max_concurrent))

@frappe.whitelist()
def request_campaign_approval(campaign_name, reason=""):
	"""Demande d'approbation pour une campagne"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		
		if not has_campaign_permission(campaign):
			frappe.throw(_("Permission insuffisante"))
		
		# Créer une demande d'approbation
		approval_request = frappe.get_doc({
			"doctype": "SMS Campaign Approval",
			"campaign": campaign_name,
			"requested_by": frappe.session.user,
			"reason": reason,
			"estimated_cost": campaign.total_sms_cost,
			"sms_count": campaign.total_customers,
			"status": "Pending"
		})
		approval_request.insert()
		
		# Notifier les approbateurs
		notify_approvers(approval_request)
		
		return {
			"success": True,
			"message": "Demande d'approbation envoyée",
			"approval_id": approval_request.name
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur demande approbation: {e}")
		return {
			"success": False,
			"message": str(e)
		}

def notify_approvers(approval_request):
	"""Notifie les approbateurs d'une demande"""
	try:
		# Récupérer les utilisateurs avec le rôle d'approbateur
		approvers = frappe.db.sql("""
			SELECT DISTINCT u.email, u.full_name
			FROM `tabUser` u
			JOIN `tabHas Role` hr ON u.name = hr.parent
			WHERE hr.role IN ('SMS Manager', 'System Manager')
			AND u.enabled = 1
			AND u.email IS NOT NULL
		""", as_dict=True)
		
		if not approvers:
			return
		
		# Envoyer email de notification
		subject = f"Demande d'approbation campagne SMS: {approval_request.campaign}"
		message = f"""
		<h3>Demande d'approbation de campagne SMS</h3>
		<p><strong>Campagne:</strong> {approval_request.campaign}</p>
		<p><strong>Demandeur:</strong> {approval_request.requested_by}</p>
		<p><strong>Nombre de SMS:</strong> {approval_request.sms_count}</p>
		<p><strong>Coût estimé:</strong> {approval_request.estimated_cost}€</p>
		<p><strong>Raison:</strong> {approval_request.reason}</p>
		
		<p><a href="/app/sms-campaign-approval/{approval_request.name}">Voir la demande</a></p>
		"""
		
		recipients = [approver.email for approver in approvers]
		
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			header=["Demande d'approbation SMS", "orange"]
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur notification approbateurs: {e}")

def log_sms_activity(campaign, action, details=""):
	"""Log les activités SMS pour audit"""
	try:
		log_entry = frappe.get_doc({
			"doctype": "SMS Campaign Log",
			"campaign": campaign,
			"user": frappe.session.user,
			"action": action,
			"details": details,
			"timestamp": frappe.utils.now(),
			"ip_address": frappe.local.request.environ.get('REMOTE_ADDR') if frappe.local.request else None
		})
		log_entry.insert(ignore_permissions=True)
		
	except Exception as e:
		frappe.log_error(f"Erreur log activité SMS: {e}")

@frappe.whitelist()
def validate_phone_consent(phone_number, campaign_type="marketing"):
	"""Vérifie le consentement pour un numéro de téléphone"""
	try:
		# Rechercher le client par numéro de téléphone
		customers = frappe.db.sql("""
			SELECT name, sms_opt_out
			FROM `tabCustomer`
			WHERE mobile_no = %s OR phone = %s
		""", (phone_number, phone_number), as_dict=True)
		
		if customers:
			customer = customers[0]
			if customer.sms_opt_out:
				return {
					"success": False,
					"message": "Client a refusé les SMS marketing"
				}
		
		# Vérifier la liste de blocage
		blocked = frappe.db.exists("SMS Blacklist", {"phone_number": phone_number})
		if blocked:
			return {
				"success": False,
				"message": "Numéro dans la liste de blocage"
			}
		
		return {
			"success": True,
			"message": "Consentement validé"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur validation consentement: {e}")
		return {
			"success": False,
			"message": "Erreur validation consentement"
		}

def enforce_gdpr_compliance():
	"""Applique la conformité RGPD"""
	try:
		# Anonymiser les données anciennes
		retention_days = frappe.db.get_single_value("System Settings", "sms_data_retention_days") or 1095
		cutoff_date = frappe.utils.add_days(frappe.utils.today(), -retention_days)
		
		# Anonymiser les anciennes campagnes
		old_campaigns = frappe.db.sql("""
			SELECT name FROM `tabSMS Pricing Campaign`
			WHERE creation < %s AND anonymized != 1
		""", cutoff_date, as_dict=True)
		
		for campaign in old_campaigns:
			anonymize_campaign_data(campaign.name)
		
	except Exception as e:
		frappe.log_error(f"Erreur conformité RGPD: {e}")

def anonymize_campaign_data(campaign_name):
	"""Anonymise les données d'une campagne"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		
		# Anonymiser les données sensibles
		for item in campaign.pricing_items:
			item.customer_mobile = "***ANONYMIZED***"
			item.customer_name = "Client Anonyme"
		
		campaign.anonymized = 1
		campaign.save(ignore_permissions=True)
		
		frappe.logger().info(f"Campagne anonymisée: {campaign_name}")
		
	except Exception as e:
		frappe.log_error(f"Erreur anonymisation campagne {campaign_name}: {e}")

# Décorateurs de sécurité

def require_sms_permission(f):
	"""Décorateur pour exiger les permissions SMS"""
	def wrapper(*args, **kwargs):
		validate_sms_sending_permission()
		return f(*args, **kwargs)
	return wrapper

def log_sms_action(action):
	"""Décorateur pour logger les actions SMS"""
	def decorator(f):
		def wrapper(*args, **kwargs):
			result = f(*args, **kwargs)
			campaign = kwargs.get('campaign_name') or (args[0] if args else None)
			log_sms_activity(campaign, action, f"Fonction: {f.__name__}")
			return result
		return wrapper
	return decorator

def rate_limit_sms(max_per_minute=10):
	"""Décorateur pour limiter le taux d'envoi SMS"""
	def decorator(f):
		def wrapper(*args, **kwargs):
			user = frappe.session.user
			cache_key = f"sms_rate_limit_{user}"
			
			# Vérifier le cache Redis/mémoire
			current_count = frappe.cache().get(cache_key) or 0
			
			if current_count >= max_per_minute:
				frappe.throw(_("Limite de débit atteinte. Réessayez dans 1 minute."))
			
			# Incrémenter le compteur
			frappe.cache().set(cache_key, current_count + 1, expires_in_sec=60)
			
			return f(*args, **kwargs)
		return wrapper
	return decorator