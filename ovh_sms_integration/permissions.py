# -*- coding: utf-8 -*-
"""Gestion des permissions et sécurité pour les campagnes SMS.

Ce module gère les permissions, quotas, et la sécurité pour les campagnes SMS.
Il fournit les fonctionnalités de:
- Permissions basées sur les rôles (System Manager, SMS Manager, SMS User)
- Quotas journaliers par utilisateur
- Limites de sécurité par campagne
- Validation du consentement RGPD
- Audit et logging des activités
- Anonymisation des données anciennes
- Rate limiting et contrôle d'accès
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable

import frappe
from frappe import _

if TYPE_CHECKING:
	from frappe.model.document import Document

def get_campaign_permission_query_conditions(user: str | None = None) -> str:
	"""Génère les conditions SQL pour filtrer les campagnes SMS par permissions.

	Args:
		user: Nom d'utilisateur optionnel. Si None, utilise l'utilisateur courant.

	Returns:
		str: Condition SQL pour filtrer les campagnes accessibles.
			 - "" = toutes les campagnes (System Manager)
			 - Condition company pour SMS Manager
			 - Condition owner pour SMS User
			 - "1=0" = aucun accès

	Example:
		>>> conditions = get_campaign_permission_query_conditions("user@example.com")
		>>> campaigns = frappe.db.sql(f"SELECT * FROM `tabSMS Pricing Campaign` WHERE {conditions}")

	Note:
		Appelée automatiquement par Frappe pour filtrer les listes de documents.
	"""
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

def has_campaign_permission(doc: "Document", user: str | None = None) -> bool:
	"""Vérifie si l'utilisateur a les permissions sur une campagne.

	Args:
		doc: Document SMS Pricing Campaign à vérifier.
		user: Nom d'utilisateur optionnel. Si None, utilise l'utilisateur courant.

	Returns:
		bool: True si l'utilisateur a accès, False sinon.

	Note:
		Hiérarchie de permissions:
		- System Manager: accès total
		- SMS Manager: campagnes de leur société
		- SMS User: leurs propres campagnes
	"""
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

def validate_sms_permissions(doc: "Document", method: str) -> None:
	"""Validation des permissions lors de la sauvegarde.

	Args:
		doc: Document SMS Pricing Campaign à valider.
		method: Nom de la méthode (before_save, before_insert, etc.).

	Raises:
		frappe.exceptions.PermissionError: Si permissions insuffisantes.

	Note:
		Hook appelé automatiquement par Frappe lors de la sauvegarde.
		Ignore les vérifications durant install/migrate.
	"""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	
	if not has_campaign_permission(doc):
		frappe.throw(_("Permissions insuffisantes pour cette campagne"))

def validate_sms_sending_permission(user: str | None = None) -> None:
	"""Vérifie les permissions d'envoi de SMS.

	Args:
		user: Nom d'utilisateur optionnel. Si None, utilise l'utilisateur courant.

	Raises:
		frappe.exceptions.PermissionError: Si l'utilisateur n'a pas les permissions.
		frappe.exceptions.ValidationError: Si le quota est atteint.

	Note:
		Vérifie:
		- Présence d'un rôle requis (SMS Manager, SMS User, System Manager)
		- Quota journalier de l'utilisateur
	"""
	if not user:
		user = frappe.session.user
	
	required_roles = ["SMS Manager", "SMS User", "System Manager"]
	user_roles = frappe.get_roles(user)
	
	if not any(role in user_roles for role in required_roles):
		frappe.throw(_("Permission d'envoi SMS requise"))
	
	# Vérification des quotas utilisateur
	check_user_sms_quota(user)

def check_user_sms_quota(user: str) -> int:
	"""Vérifie le quota SMS de l'utilisateur.

	Args:
		user: Nom d'utilisateur.

	Returns:
		int: Nombre de SMS restants dans le quota journalier.

	Raises:
		frappe.exceptions.ValidationError: Si quota atteint ou non défini.

	Note:
		Quotas par rôle:
		- System Manager: 9999 SMS/jour
		- SMS Manager: 500 SMS/jour
		- SMS User: 100 SMS/jour
		- TODO: Créer doctype SMS Campaign Log pour le suivi
	"""
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
		
		# TODO: Créer doctype SMS Campaign Log pour le suivi
		# Compter les SMS envoyés aujourd'hui
		# NOTE: SMS Campaign Log n'existe pas encore, donc on considère 0 SMS envoyés
		# jusqu'à ce que le doctype soit créé
		sent_today = 0

		# Vérifier si le doctype existe avant de faire la requête
		if frappe.db.exists("DocType", "SMS Campaign Log"):
			try:
				today = datetime.now().date()
				sent_today = frappe.db.count("SMS Campaign Log", {
					"sender": user,
					"date": today,
					"status": "Sent"
				})
			except Exception as log_error:
				frappe.log_error(
					f"Erreur comptage SMS Campaign Log: {log_error}",
					"SMS Quota Warning"
				)
				sent_today = 0

		if sent_today >= max_quota:
			frappe.throw(_("Quota SMS journalier atteint ({0}/{1})").format(sent_today, max_quota))

		return max_quota - sent_today

	except frappe.exceptions.ValidationError:
		# Re-raise les ValidationError (quota atteint, pas de permission, etc.)
		raise
	except Exception as e:
		frappe.log_error(f"Erreur vérification quota SMS: {e}", "SMS Quota Error")
		# En cas d'erreur, lever une exception au lieu de retourner 0
		frappe.throw(_("Impossible de vérifier le quota SMS: {0}").format(str(e)))

@frappe.whitelist()
def get_user_sms_quota() -> dict[str, Any]:
	"""API pour récupérer le quota SMS utilisateur.

	Returns:
		dict[str, Any]: Résultat avec:
			- success: bool
			- remaining_quota: int (si succès)
			- message: str (si erreur)

	Note:
		Whitelisted API endpoint accessible depuis le frontend.
	"""
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

def setup_campaign_security() -> None:
	"""Configure la sécurité des campagnes SMS.

	Note:
		Appelée lors de l'installation de l'app pour:
		- Créer les rôles SMS nécessaires
		- Configurer les permissions par défaut
		- Définir les limites de sécurité
	"""
	# Création des rôles si ils n'existent pas
	create_sms_roles()
	
	# Configuration des permissions par défaut
	setup_default_permissions()
	
	# Configuration des limites de sécurité
	setup_security_limits()

def create_sms_roles() -> None:
	"""Crée les rôles SMS nécessaires.

	Note:
		Crée les rôles suivants s'ils n'existent pas:
		- Campaign Manager: gestion complète des campagnes
		- SMS Operator: exécution uniquement
		- SMS Viewer: lecture seule
	"""
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

def setup_default_permissions() -> None:
	"""Configure les permissions par défaut pour les campagnes.

	Note:
		Configure les permissions pour:
		- SMS Pricing Campaign: permissions CRUD par rôle
		- SMS Pricing Item: permissions sur child table
	"""
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

def setup_doctype_permissions(doctype: str, permissions: list[dict[str, Any]]) -> None:
	"""Configure les permissions pour un DocType spécifique.

	Args:
		doctype: Nom du DocType à configurer.
		permissions: Liste de dictionnaires de permissions par rôle.

	Note:
		Crée les DocPerm uniquement s'ils n'existent pas déjà.
		Logue les erreurs sans bloquer l'installation.
	"""
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

def setup_security_limits() -> None:
	"""Configure les limites de sécurité.

	Note:
		Sauvegarde dans System Settings:
		- max_sms_per_campaign: 10000
		- max_campaigns_per_user_per_day: 5
		- max_concurrent_campaigns: 3
		- require_approval_above_amount: 5000€
		- require_approval_above_sms_count: 1000
	"""
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

def validate_campaign_limits(doc: "Document", method: str) -> None:
	"""Valide les limites de sécurité pour une campagne.

	Args:
		doc: Document SMS Pricing Campaign à valider.
		method: Nom de la méthode (before_save, validate, etc.).

	Raises:
		frappe.exceptions.ValidationError: Si limites dépassées.

	Note:
		Hook appelé automatiquement par Frappe lors de la validation.
		Définit requires_approval=1 si montant ou nombre > seuils.
	"""
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

def check_concurrent_campaigns(user: str | None = None) -> None:
	"""Vérifie le nombre de campagnes simultanées.

	Args:
		user: Nom d'utilisateur optionnel. Si None, utilise l'utilisateur courant.

	Raises:
		frappe.exceptions.ValidationError: Si limite de campagnes simultanées atteinte.

	Note:
		Compte les campagnes avec status="Prêt" ou "En cours" et docstatus=1.
		Limite par défaut: 3 campagnes simultanées.
		TODO: Convertir SQL en ORM Frappe
	"""
	if not user:
		user = frappe.session.user
	
	max_concurrent = frappe.db.get_single_value("System Settings", "sms_max_concurrent_campaigns") or 3

	# TODO: Convertir SQL en ORM Frappe
	active_campaigns = frappe.db.count("SMS Pricing Campaign", {
		"owner": user,
		"status": ["in", ["Prêt", "En cours"]],
		"docstatus": 1
	})
	
	if active_campaigns >= max_concurrent:
		frappe.throw(_("Limite atteinte: maximum {0} campagnes simultanées").format(max_concurrent))

@frappe.whitelist()
def request_campaign_approval(campaign_name: str, reason: str = "") -> dict[str, Any]:
	"""Demande d'approbation pour une campagne.

	Args:
		campaign_name: Nom de la campagne nécessitant approbation.
		reason: Raison optionnelle de la demande.

	Returns:
		dict[str, Any]: Résultat avec:
			- success: bool
			- message: str
			- approval_id: str (si succès)

	Note:
		- Whitelisted API endpoint
		- Crée un document SMS Campaign Approval
		- Notifie les approbateurs par email
		- TODO: Créer doctype SMS Campaign Approval
	"""
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

def notify_approvers(approval_request: "Document") -> None:
	"""Notifie les approbateurs d'une demande.

	Args:
		approval_request: Document SMS Campaign Approval à notifier.

	Note:
		- Envoie email aux users avec role SMS Manager ou System Manager
		- Inclut lien vers la demande d'approbation
		- Utilise template Jinja pour l'HTML
	"""
	try:
		# Récupérer les utilisateurs avec le rôle d'approbateur (ORM Frappe)
		manager_roles = frappe.get_all(
			"Has Role",
			filters={
				"role": ["in", ["SMS Manager", "System Manager"]],
				"parenttype": "User"
			},
			fields=["parent"],
			distinct=True
		)

		if not manager_roles:
			return

		# Récupérer les détails des utilisateurs actifs
		approvers = []
		for role_assignment in manager_roles:
			user = frappe.get_doc("User", role_assignment.parent)
			if user.enabled and user.email:
				approvers.append({
					"email": user.email,
					"full_name": user.full_name
				})

		if not approvers:
			return

		# Rendre le template Jinja pour l'email
		subject = f"Demande d'approbation campagne SMS: {approval_request.campaign}"
		message = frappe.render_template(
			"ovh_sms_integration/templates/emails/campaign_approval_request.html",
			{
				"campaign": approval_request.campaign,
				"requested_by": approval_request.requested_by,
				"sms_count": approval_request.sms_count,
				"estimated_cost": approval_request.estimated_cost,
				"reason": approval_request.reason,
				"approval_link": f"/app/sms-campaign-approval/{approval_request.name}"
			}
		)

		recipients = [approver.email for approver in approvers]
		
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			header=["Demande d'approbation SMS", "orange"]
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur notification approbateurs: {e}")

def log_sms_activity(campaign: str, action: str, details: str = "") -> None:
	"""Log les activités SMS pour audit.

	Args:
		campaign: Nom de la campagne.
		action: Type d'action effectuée.
		details: Détails optionnels de l'action.

	Note:
		- Enregistre: user, timestamp, IP address
		- Utilise ignore_permissions pour garantir le logging
		- TODO: Créer doctype SMS Campaign Log
	"""
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
def validate_phone_consent(phone_number: str, campaign_type: str = "marketing") -> dict[str, Any]:
	"""Vérifie le consentement RGPD pour un numéro de téléphone.

	Args:
		phone_number: Numéro de téléphone à vérifier.
		campaign_type: Type de campagne (marketing, transactionnel, etc.).

	Returns:
		dict[str, Any]: Résultat avec:
			- success: bool
			- message: str (raison du refus ou validation)

	Note:
		- Whitelisted API endpoint
		- Vérifie sms_opt_out dans Customer
		- Vérifie SMS Blacklist
		- TODO: Créer doctype SMS Blacklist
	"""
	try:
		# Rechercher le client par numéro de téléphone (ORM Frappe)
		# Note: OR condition requires checking both fields separately
		customers = frappe.get_all(
			"Customer",
			filters={
				"mobile_no": phone_number
			},
			fields=["name", "sms_opt_out"],
			limit=1
		)

		if not customers:
			# Try with phone field if mobile_no didn't match
			customers = frappe.get_all(
				"Customer",
				filters={
					"phone": phone_number
				},
				fields=["name", "sms_opt_out"],
				limit=1
			)

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

def enforce_gdpr_compliance() -> None:
	"""Applique la conformité RGPD.

	Note:
		- Anonymise les campagnes de plus de 3 ans (1095 jours)
		- Appelée par scheduler quotidien
		- Respecte le droit à l'oubli
	"""
	try:
		# Anonymiser les données anciennes
		retention_days = frappe.db.get_single_value("System Settings", "sms_data_retention_days") or 1095
		cutoff_date = frappe.utils.add_days(frappe.utils.today(), -retention_days)

		# Anonymiser les anciennes campagnes (ORM Frappe)
		old_campaigns = frappe.get_all(
			"SMS Pricing Campaign",
			filters={
				"creation": ["<", cutoff_date],
				"anonymized": ["!=", 1]
			},
			pluck="name"
		)

		for campaign_name in old_campaigns:
			anonymize_campaign_data(campaign_name)
		
	except Exception as e:
		frappe.log_error(f"Erreur conformité RGPD: {e}")

def anonymize_campaign_data(campaign_name: str) -> None:
	"""Anonymise les données d'une campagne.

	Args:
		campaign_name: Nom de la campagne à anonymiser.

	Note:
		- Remplace customer_mobile par "***ANONYMIZED***"
		- Remplace customer_name par "Client Anonyme"
		- Marque anonymized=1 sur le document
		- Utilise ignore_permissions pour garantir l'anonymisation
	"""
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


def require_sms_permission(f: Callable[..., Any]) -> Callable[..., Any]:
	"""Décorateur pour exiger les permissions SMS.

	Args:
		f: Fonction à décorer.

	Returns:
		Callable: Fonction décorée avec validation de permissions.

	Raises:
		frappe.exceptions.PermissionError: Si permissions insuffisantes.

	Example:
		>>> @require_sms_permission
		... def send_bulk_sms(recipients):
		...     pass
	"""
	def wrapper(*args: Any, **kwargs: Any) -> Any:
		validate_sms_sending_permission()
		return f(*args, **kwargs)
	return wrapper

def log_sms_action(action: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
	"""Décorateur pour logger les actions SMS.

	Args:
		action: Type d'action à logger.

	Returns:
		Callable: Décorateur de fonction.

	Example:
		>>> @log_sms_action("send")
		... def send_campaign(campaign_name):
		...     pass
	"""
	def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
		def wrapper(*args: Any, **kwargs: Any) -> Any:
			result = f(*args, **kwargs)
			campaign = kwargs.get('campaign_name') or (args[0] if args else None)
			if campaign:
				log_sms_activity(campaign, action, f"Fonction: {f.__name__}")
			return result
		return wrapper
	return decorator

def rate_limit_sms(max_per_minute: int = 10) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
	"""Décorateur pour limiter le taux d'envoi SMS.

	Args:
		max_per_minute: Nombre maximum d'appels par minute.

	Returns:
		Callable: Décorateur de fonction.

	Raises:
		frappe.exceptions.ValidationError: Si limite de débit atteinte.

	Example:
		>>> @rate_limit_sms(max_per_minute=5)
		... def send_sms(phone, message):
		...     pass

	Note:
		Utilise frappe.cache() avec TTL de 60 secondes.
	"""
	def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
		def wrapper(*args: Any, **kwargs: Any) -> Any:
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