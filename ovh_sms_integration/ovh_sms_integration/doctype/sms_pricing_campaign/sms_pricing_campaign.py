# -*- coding: utf-8 -*-
"""SMS Pricing Campaign doctype.

Ce module gère les campagnes de tarification SMS pour les clients.
Il fournit les fonctionnalités de:
- Création de campagnes de prix personnalisés par client/article
- Calcul automatique des marges et prix de vente
- Envoi de SMS de tarification en masse
- Suivi des envois et statistiques
- Templates personnalisables pour les messages
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _
from frappe.model.document import Document
from jinja2 import Template

if TYPE_CHECKING:
	from ovh_sms_integration.types import CampaignStats, SMSResult

class SMSPricingCampaign(Document):
	"""DocType de campagne de tarification SMS.

	Gère les campagnes de prix personnalisés envoyées par SMS aux clients.

	Attributes:
		campaign_name (str): Nom de la campagne
		pricing_items (list): Lignes de tarification (client + article + prix)
		message_template (str): Template Jinja2 du message
		status (str): Statut ("Brouillon", "Prêt", "Envoyé", etc.)
		total_items (int): Nombre total d'articles
		total_customers (int): Nombre de clients uniques
		total_sms_cost (float): Coût total estimé des SMS
		estimated_revenue (float): Revenu total estimé
		profit_potential (float): Profit total estimé
		average_margin_percent (float): Marge moyenne en %
	"""

	def validate(self) -> None:
		"""Valide les données de la campagne avant sauvegarde.

		Raises:
			frappe.ValidationError: Si aucun article n'est ajouté.
			frappe.ValidationError: Si validation des lignes échoue.

		Note:
			- Valide toutes les pricing_items
			- Calcule les totaux automatiquement
			- Met à jour le statut selon les données
		"""
		if not self.pricing_items:
			frappe.throw(_("Veuillez ajouter au moins un article et client"))
		
		# Validation des lignes
		for item in self.pricing_items:
			self.validate_pricing_item(item)
		
		# Calcul des totaux
		self.calculate_totals()
		
		# Mise à jour du statut
		self.update_status()

	def before_save(self) -> None:
		"""Actions avant sauvegarde.

		Note:
			- Recalcule les totaux pour assurer cohérence
			- Appelé automatiquement par Frappe avant save()
		"""
		self.calculate_totals()

	def validate_pricing_item(self, item: Any) -> None:
		"""Valide une ligne de tarification.

		Vérifie tous les champs requis et calcule automatiquement
		les prix et marges pour une ligne de campagne.

		Args:
			item: Ligne de tarification (child table row).

		Raises:
			frappe.ValidationError: Si client manquant.
			frappe.ValidationError: Si article manquant.
			frappe.ValidationError: Si mobile manquant et non récupérable.
			frappe.ValidationError: Si valuation_rate invalide.
			frappe.ValidationError: Si marge négative.

		Note:
			- Récupère automatiquement le mobile du client si absent
			- Force la devise à EUR
			- Calcule automatiquement les prix via calculate_item_pricing()
		"""
		if not item.customer:
			frappe.throw(_("Client requis dans ligne {0}").format(item.idx))
		
		if not item.item_code:
			frappe.throw(_("Article requis dans ligne {0}").format(item.idx))
		
		if not item.customer_mobile:
			# Essayer de récupérer le mobile du client
			mobile = self.get_customer_mobile(item.customer)
			if mobile:
				item.customer_mobile = mobile
			else:
				frappe.throw(_("Numéro mobile requis pour le client {0}").format(item.customer))
		
		# Validation du taux de valorisation
		if not item.valuation_rate or item.valuation_rate <= 0:
			frappe.throw(_("Taux de valorisation requis pour {0}").format(item.item_name or item.item_code))
		
		# Validation de la marge
		if item.margin_amount_eur and item.margin_amount_eur < 0:
			frappe.throw(_("La marge ne peut pas être négative pour {0}").format(item.item_name or item.item_code))
		
		# Force EUR comme devise
		item.currency = "EUR"
		
		# Calcul automatique des prix
		self.calculate_item_pricing(item)

	def get_customer_mobile(self, customer_name: str) -> str | None:
		"""Récupère le numéro mobile d'un client.

		Recherche le mobile dans le document Customer puis dans les contacts liés.

		Args:
			customer_name: Nom/ID du client.

		Returns:
			str | None: Numéro mobile formaté, ou None si non trouvé.

		Note:
			- TODO: Convertir SQL en ORM Frappe
			- Vérifie customer.mobile_no en premier
			- Fallback sur Contact via Dynamic Link
			- Formate automatiquement le numéro via format_phone_number()
			- Les erreurs sont loggées et retournent None
		"""
		try:
			customer = frappe.get_doc("Customer", customer_name)

			# Vérifier le champ mobile du customer
			if hasattr(customer, 'mobile_no') and customer.mobile_no:
				return self.format_phone_number(customer.mobile_no)

			# Chercher dans les contacts liés (ORM Frappe)
			# Récupérer les Dynamic Links pour ce client
			dynamic_links = frappe.get_all(
				"Dynamic Link",
				filters={
					"link_doctype": "Customer",
					"link_name": customer_name
				},
				fields=["parent"]
			)

			if dynamic_links:
				contact_names = [link.parent for link in dynamic_links]
				contacts = frappe.get_all(
					"Contact",
					filters=[
						["name", "in", contact_names],
						["mobile_no", "is", "set"]
					],
					fields=["mobile_no", "phone"],
					limit=1
				)

				# Fallback si pas de mobile_no mais un phone
				if not contacts:
					contacts = frappe.get_all(
						"Contact",
						filters=[
							["name", "in", contact_names],
							["phone", "is", "set"]
						],
						fields=["mobile_no", "phone"],
						limit=1
					)

				if contacts:
					mobile = contacts[0].mobile_no or contacts[0].phone
					return self.format_phone_number(mobile)
				
		except Exception as e:
			frappe.log_error(f"Erreur récupération mobile client {customer_name}: {e}")
		
		return None

	def format_phone_number(self, phone: str | None) -> str | None:
		"""Formate un numéro de téléphone au format international français.

		Nettoie et convertit les numéros au format +33.

		Args:
			phone: Numéro de téléphone brut.

		Returns:
			str | None: Numéro formaté (+33...) ou numéro original si non français.

		Example:
			>>> campaign.format_phone_number("06 12 34 56 78")
			'+33612345678'
			>>> campaign.format_phone_number("+33612345678")
			'+33612345678'

		Note:
			- Supprime les espaces, points, tirets
			- Convertit 06... en +336...
			- Laisse inchangé si déjà au format international
		"""
		if not phone:
			return phone
		
		import re
		# Supprimer tous les caractères non numériques sauf le +
		cleaned = re.sub(r'[^\d+]', '', str(phone))
		
		# Format français
		if cleaned.startswith('0'):
			cleaned = '+33' + cleaned[1:]
		elif not cleaned.startswith('+'):
			cleaned = '+33' + cleaned
		
		return cleaned

	def calculate_item_pricing(self, item: Any) -> None:
		"""Calcule le prix avec marge pour un article.

		Formule: Prix final = Taux de valorisation + Marge en euros
		Montant total = Prix final × Quantité

		Args:
			item: Ligne de tarification (child table row).

		Note:
			- Utilise valuation_rate comme prix de base
			- Ajoute margin_amount_eur (marge en euros fixes)
			- Calcule amount = final_price × qty
			- Les erreurs sont loggées et un prix fallback est utilisé
		"""
		try:
			# Nouvelle logique: Prix final = Taux de valorisation + Marge en euros
			item.final_price = (item.valuation_rate or 0) + (item.margin_amount_eur or 0)
			
			# Montant total = Prix final × Quantité
			item.amount = item.final_price * (item.qty or 1)
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul prix article: {e}")
			item.final_price = item.valuation_rate or 0
			item.amount = item.final_price * (item.qty or 1)

	def calculate_totals(self) -> None:
		"""Calcule les totaux et statistiques de la campagne.

		Met à jour tous les champs de totalisation du document:
		- total_items: Nombre de lignes
		- total_customers: Nombre de clients uniques
		- total_sms_cost: Coût estimé des SMS (0.10€ par SMS)
		- estimated_revenue: Revenu total estimé
		- profit_potential: Marge totale estimée
		- average_margin_percent: Pourcentage de marge moyen

		Note:
			- Calcule marge = margin_amount_eur × qty pour chaque ligne
			- Coût SMS = 0.10€ × nombre de clients uniques
			- Marge % = (marge totale / valorisation totale) × 100
			- Les erreurs sont loggées mais ne bloquent pas
		"""
		try:
			if not self.pricing_items:
				return
			
			total_items = len(self.pricing_items)
			unique_customers = set()
			total_amount = 0
			total_margin = 0
			total_valuation = 0
			sms_cost = 0.10  # Coût estimé par SMS
			
			for item in self.pricing_items:
				if item.customer:
					unique_customers.add(item.customer)
				total_amount += item.amount or 0
				
				# Calcul de la marge totale (marge euros × quantité)
				margin_amount = (item.margin_amount_eur or 0) * (item.qty or 1)
				total_margin += margin_amount
				
				# Calcul du coût total de valorisation
				valuation_amount = (item.valuation_rate or 0) * (item.qty or 1)
				total_valuation += valuation_amount
			
			self.total_items = total_items
			self.total_customers = len(unique_customers)
			self.total_sms_cost = self.total_customers * sms_cost
			self.estimated_revenue = total_amount
			self.profit_potential = total_margin
			
			# Calcul pourcentage de marge moyen
			if total_valuation > 0:
				self.average_margin_percent = (total_margin / total_valuation) * 100
			else:
				self.average_margin_percent = 0
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul totaux campagne: {e}")

	def update_status(self) -> None:
		"""Met à jour le statut de la campagne selon les envois.

		Statuts possibles:
		- "Brouillon": Pas prête ou aucun SMS envoyé
		- "Prêt": Validée et prête à envoyer
		- "Partiellement envoyé": Certains SMS envoyés
		- "Envoyé": Tous les SMS envoyés

		Note:
			- Compte le nombre de sms_sent dans pricing_items
			- Vérifie validate_ready_to_send() pour statut "Prêt"
			- Appelé automatiquement dans validate()
		"""
		if not self.pricing_items:
			self.status = "Brouillon"
			return
		
		sent_count = sum(1 for item in self.pricing_items if item.sms_sent)
		total_count = len(self.pricing_items)
		
		if sent_count == 0:
			if self.validate_ready_to_send():
				self.status = "Prêt"
			else:
				self.status = "Brouillon"
		elif sent_count == total_count:
			self.status = "Envoyé"
		else:
			self.status = "Partiellement envoyé"

	def validate_ready_to_send(self) -> bool:
		"""Vérifie si la campagne est prête à être envoyée.

		Returns:
			bool: True si toutes les lignes ont customer_mobile et final_price.

		Note:
			- Vérifie que toutes les lignes ont un mobile
			- Vérifie que toutes les lignes ont un final_price
			- Retourne False si pricing_items vide
		"""
		if not self.pricing_items:
			return False
		
		for item in self.pricing_items:
			if not item.customer_mobile or not item.final_price:
				return False
		
		return True

	def format_sms_message(self, item: Any) -> str:
		"""Formate le message SMS pour un client/article.

		Rend le template Jinja2 avec les données de la ligne.

		Args:
			item: Ligne de tarification (child table row).

		Returns:
			str: Message SMS formaté. En cas d'erreur, retourne un message fallback.

		Example:
			>>> template = "Bonjour {{customer_name}}, {{item_name}} à {{final_price}}€"
			>>> message = campaign.format_sms_message(item)
			>>> # "Bonjour ACME Corp, Fuel Oil à 150.50€"

		Note:
			- Variables disponibles: customer_name, item_name, item_code,
			  final_price, amount, currency, valuation_rate, margin_eur,
			  qty, company, campaign_title
			- Formate les prix avec 2 décimales
			- Force currency à EUR
			- Les erreurs retournent un message simple fallback
		"""
		try:
			template = self.sms_template or "Bonjour {{customer_name}}, nous vous proposons {{item_name}} au prix de {{final_price}}€."
			
			# Préparation du contexte
			context = {
				'customer_name': item.customer_name or item.customer,
				'item_name': item.item_name or item.item_code,
				'item_code': item.item_code,
				'final_price': "{:.2f}".format(item.final_price or 0),
				'amount': "{:.2f}".format(item.amount or 0),
				'currency': "EUR",  # Force EUR
				'valuation_rate': "{:.2f}".format(item.valuation_rate or 0),
				'margin_eur': "{:.2f}".format(item.margin_amount_eur or 0),
				'qty': item.qty or 1,
				'company': self.company or frappe.defaults.get_user_default("Company") or "",
				'campaign_title': self.title or ""
			}
			
			# Formatage avec Jinja2
			template_obj = Template(template)
			message = template_obj.render(**context)
			
			return message
			
		except Exception as e:
			frappe.log_error(f"Erreur formatage message SMS: {e}")
			return f"Offre {item.item_name} à {item.final_price}€ pour {item.customer_name}"

	def send_sms_to_item(self, item: Any) -> dict[str, Any]:
		"""Envoie un SMS pour une ligne spécifique.

		Formate et envoie le SMS pour une ligne de campagne, puis
		met à jour le statut d'envoi.

		Args:
			item: Ligne de tarification (child table row).

		Returns:
			dict[str, Any]: Résultat avec success et message.

		Note:
			- Vérifie que SMS pas déjà envoyé (item.sms_sent)
			- Vérifie que customer_mobile existe
			- Formate le message via format_sms_message()
			- Délègue l'envoi à OVH SMS Settings
			- Met à jour item.sms_sent et item.sms_status si succès
			- Met à jour item.sms_error_message si échec
			- Sauvegarde le document automatiquement après mise à jour
		"""
		try:
			if item.sms_sent:
				return {"success": False, "message": "SMS déjà envoyé"}
			
			if not item.customer_mobile:
				return {"success": False, "message": "Numéro mobile manquant"}
			
			# Formatage du message
			message = self.format_sms_message(item)
			
			# Envoi via OVH SMS
			sms_settings = frappe.get_single('OVH SMS Settings')
			if not sms_settings.enabled:
				return {"success": False, "message": "OVH SMS non activé"}
			
			result = sms_settings.send_sms(message, item.customer_mobile)
			
			# Mise à jour du statut
			if result and result.get('success'):
				item.sms_sent = 1
				item.sms_status = "Envoyé"
				
				return {"success": True, "message": "SMS envoyé avec succès"}
			else:
				item.sms_status = "Échoué"
				error_msg = result.get('message', 'Erreur inconnue') if result else 'Pas de réponse'
				
				return {"success": False, "message": error_msg}
		
		except Exception as e:
			error_msg = f"Erreur envoi SMS: {str(e)}"
			item.sms_status = "Échoué"
			frappe.log_error(error_msg)
			
			return {"success": False, "message": error_msg}

	def send_all_sms(self) -> dict[str, Any]:
		"""Envoie tous les SMS de la campagne.

		Traite toutes les lignes sélectionnées et non encore envoyées.

		Returns:
			dict[str, Any]: Statistiques d'envoi avec:
				- sent (int): Nombre de SMS envoyés
				- failed (int): Nombre de SMS échoués
				- details (list): Liste des résultats par ligne
				- error (str): Message d'erreur si exception globale

		Note:
			- Traite uniquement les lignes avec selected_for_sending=True
			- Ignore les lignes déjà envoyées (sms_sent=True)
			- Met à jour les statistiques via update_sending_statistics()
			- Sauvegarde automatiquement le document après traitement
			- Les erreurs individuelles n'arrêtent pas le batch
		"""
		results = {
			"sent": 0,
			"failed": 0,
			"details": []
		}
		
		try:
			for item in self.pricing_items:
				if item.selected_for_sending and not item.sms_sent:
					result = self.send_sms_to_item(item)
					
					if result["success"]:
						results["sent"] += 1
					else:
						results["failed"] += 1
					
					results["details"].append({
						"customer": item.customer_name or item.customer,
						"item": item.item_name or item.item_code,
						"success": result["success"],
						"message": result["message"]
					})
			
			# Mise à jour des statistiques
			self.update_sending_statistics(results)
			
			# Sauvegarde
			self.save()
			
			return results
			
		except Exception as e:
			frappe.log_error(f"Erreur envoi campagne SMS: {e}")
			return {
				"sent": 0,
				"failed": len(self.pricing_items),
				"error": str(e)
			}

	def update_sending_statistics(self, results: dict[str, Any]) -> None:
		"""Met à jour les statistiques d'envoi.

		Args:
			results: Dict avec sent et failed counts.

		Note:
			- Met à jour sms_sent_count et sms_failed_count
			- Met à jour last_sent_time à maintenant
			- Appelle update_status() pour recalculer le statut
			- Les erreurs sont loggées mais ne bloquent pas
		"""
		try:
			self.sms_sent_count = (self.sms_sent_count or 0) + results["sent"]
			self.sms_failed_count = (self.sms_failed_count or 0) + results["failed"]
			self.last_sent_time = datetime.now()
			
			# Mise à jour du statut
			self.update_status()
			
		except Exception as e:
			frappe.log_error(f"Erreur mise à jour statistiques: {e}")

	def get_preview_messages(self) -> list[dict[str, Any]]:
		"""Génère un aperçu des messages pour quelques clients.

		Retourne les 3 premières lignes sélectionnées avec messages formatés.

		Returns:
			list[dict[str, Any]]: Liste de previews avec customer, mobile,
				item, price, valuation, margin, message pour chaque ligne.

		Note:
			- Limite à 3 lignes maximum
			- Utilise uniquement les lignes avec selected_for_sending=True
			- Appelle format_sms_message() pour chaque ligne
			- Les erreurs retournent une liste vide et sont loggées
		"""
		previews = []
		
		try:
			# Prendre les 3 premiers éléments sélectionnés
			selected_items = [item for item in self.pricing_items if item.selected_for_sending][:3]
			
			for item in selected_items:
				message = self.format_sms_message(item)
				previews.append({
					"customer": item.customer_name or item.customer,
					"mobile": item.customer_mobile,
					"item": item.item_name or item.item_code,
					"price": item.final_price,
					"valuation": item.valuation_rate,
					"margin": item.margin_amount_eur,
					"message": message
				})
			
			return previews
			
		except Exception as e:
			frappe.log_error(f"Erreur génération aperçu: {e}")
			return []

	def get_item_valuation_rate_internal(self, item_code: str) -> float:
		"""Récupère le taux de valorisation d'un article.

		Recherche le taux de valorisation avec plusieurs méthodes fallback.

		Args:
			item_code: Code de l'article.

		Returns:
			float: Taux de valorisation. Retourne 0 si non trouvé.

		Note:
			- Méthode 1: Dernière valorisation dans Stock Ledger Entry
			- Méthode 2: standard_rate du document Item
			- Méthode 3: Dernier prix dans Purchase Invoice Item
			- Retourne 0 si aucune méthode ne trouve de valeur
			- Les erreurs sont loggées et retournent 0
		"""
		try:
			# Méthode 1: Dernière valorisation en stock (ORM Frappe)
			valuation = frappe.get_all(
				"Stock Ledger Entry",
				filters={
					"item_code": item_code,
					"valuation_rate": [">", 0]
				},
				fields=["valuation_rate"],
				order_by="posting_date desc, posting_time desc",
				limit=1
			)

			if valuation:
				return valuation[0].valuation_rate

			# Méthode 2: Prix standard de l'article
			item_doc = frappe.get_doc("Item", item_code)
			if hasattr(item_doc, 'standard_rate') and item_doc.standard_rate:
				return item_doc.standard_rate

			# Méthode 3: Dernier prix d'achat (ORM Frappe)
			purchase_price = frappe.get_all(
				"Purchase Invoice Item",
				filters={
					"item_code": item_code,
					"rate": [">", 0]
				},
				fields=["rate"],
				order_by="creation desc",
				limit=1
			)

			if purchase_price:
				return purchase_price[0].rate
			
			return 0
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération taux valorisation interne {item_code}: {e}")
			return 0


# === MÉTHODES GLOBALES POUR L'API ===

@frappe.whitelist()
def send_all_sms(campaign_name: str) -> dict[str, Any]:
	"""API endpoint pour envoyer tous les SMS d'une campagne.

	Fonction whitelistée pour déclencher l'envoi en masse depuis l'interface.

	Args:
		campaign_name: Nom/ID de la campagne.

	Returns:
		dict[str, Any]: Résultats avec success, message, sent, failed, details.

	Raises:
		frappe.ValidationError: Si campagne non soumise (docstatus != 1).

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...send_all_sms",
		...     args: {campaign_name: "CAMP-001"},
		...     callback: function(r) {
		...         console.log("Envoyés:", r.message.sent);
		...     }
		... })

	Note:
		- Nécessite que la campagne soit soumise (docstatus=1)
		- Délègue à campaign.send_all_sms()
		- Les erreurs sont loggées et retournées dans le résultat
	"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		
		if campaign.docstatus != 1:
			return {
				"success": False,
				"message": "La campagne doit être soumise avant l'envoi"
			}
		
		results = campaign.send_all_sms()
		
		return {
			"success": True,
			"message": f"{results['sent']} SMS envoyés, {results['failed']} échecs",
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur API envoi campagne: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def send_selected_sms(campaign_name: str) -> dict[str, Any]:
	"""API endpoint pour envoyer uniquement les SMS sélectionnés.

	Fonction whitelistée pour envoyer seulement les lignes avec
	selected_for_sending=True.

	Args:
		campaign_name: Nom/ID de la campagne.

	Returns:
		dict[str, Any]: Résultat avec success, message et results.

	Note:
		- Compte les lignes selected_for_sending=True et sms_sent=False
		- Retourne erreur si aucune ligne sélectionnée
		- Délègue à campaign.send_all_sms() (qui filtre automatiquement)
	"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		
		# Compter les éléments sélectionnés non envoyés
		selected_count = sum(1 for item in campaign.pricing_items 
						   if item.selected_for_sending and not item.sms_sent)
		
		if selected_count == 0:
			return {
				"success": False,
				"message": "Aucun élément sélectionné pour l'envoi"
			}
		
		results = campaign.send_all_sms()  # Envoie seulement les sélectionnés
		
		return {
			"success": True,
			"message": f"{results['sent']} SMS envoyés sur {selected_count} sélectionnés",
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur API envoi sélectionnés: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def preview_messages(campaign_name: str) -> dict[str, Any]:
	"""API endpoint pour prévisualiser les messages SMS.

	Args:
		campaign_name: Nom/ID de la campagne.

	Returns:
		dict[str, Any]: Résultat avec success et previews (liste).

	Note:
		- Délègue à campaign.get_preview_messages()
		- Limite à 3 messages
		- Les erreurs sont loggées
	"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		previews = campaign.get_preview_messages()
		
		return {
			"success": True,
			"previews": previews
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur API aperçu: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def send_test_sms(campaign_name: str, test_mobile: str) -> dict[str, Any]:
	"""API endpoint pour envoyer un SMS de test.

	Args:
		campaign_name: Nom/ID de la campagne.
		test_mobile: Numéro de test pour recevoir le SMS.

	Returns:
		dict[str, Any]: Résultat avec success, message, content, valuation_rate,
			margin_eur, final_price.

	Note:
		- Utilise le premier article de la campagne pour le test
		- Crée une copie temporaire avec "Client Test"
		- N'enregistre PAS l'envoi du test
		- Retourne le contenu du message pour preview
	"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		
		if not campaign.pricing_items:
			return {
				"success": False,
				"message": "Aucun article dans la campagne"
			}
		
		# Utiliser le premier article pour le test
		test_item = campaign.pricing_items[0]
		
		# Créer une copie temporaire pour le test
		import copy
		test_item_copy = copy.deepcopy(test_item)
		test_item_copy.customer_name = "Client Test"
		test_item_copy.customer_mobile = test_mobile
		
		# Formatter le message
		message = campaign.format_sms_message(test_item_copy)
		
		# Envoyer le SMS
		sms_settings = frappe.get_single('OVH SMS Settings')
		if not sms_settings.enabled:
			return {
				"success": False,
				"message": "OVH SMS non activé"
			}
		
		result = sms_settings.send_sms(message, test_mobile)
		
		if result and result.get('success'):
			return {
				"success": True,
				"message": f"SMS de test envoyé vers {test_mobile}",
				"content": message,
				"valuation_rate": test_item.valuation_rate,
				"margin_eur": test_item.margin_amount_eur,
				"final_price": test_item.final_price
			}
		else:
			return {
				"success": False,
				"message": result.get('message', 'Erreur envoi SMS') if result else 'Pas de réponse'
			}
		
	except Exception as e:
		frappe.log_error(f"Erreur API test SMS: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def get_item_valuation_rate(item_code: str) -> dict[str, Any]:
	"""API endpoint pour récupérer le taux de valorisation d'un article.

	Args:
		item_code: Code de l'article.

	Returns:
		dict[str, Any]: Résultat avec success, rate et source.
			Source peut être: "Stock Ledger Entry", "Standard Rate",
			"Purchase Invoice", "No data found".

	Note:
		- Essaie 3 sources dans l'ordre
		- Retourne 0 si aucune source ne trouve de valeur
		- Les erreurs sont loggées
	"""
	try:
		# Méthode 1: Dernière valorisation en stock (ORM Frappe)
		valuation = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"item_code": item_code,
				"valuation_rate": [">", 0]
			},
			fields=["valuation_rate"],
			order_by="posting_date desc, posting_time desc",
			limit=1
		)

		if valuation:
			return {
				"success": True,
				"rate": valuation[0].valuation_rate,
				"source": "Stock Ledger Entry"
			}

		# Méthode 2: Prix standard de l'article
		item_doc = frappe.get_doc("Item", item_code)
		if hasattr(item_doc, 'standard_rate') and item_doc.standard_rate:
			return {
				"success": True,
				"rate": item_doc.standard_rate,
				"source": "Standard Rate"
			}

		# Méthode 3: Dernier prix d'achat (ORM Frappe)
		purchase_price = frappe.get_all(
			"Purchase Invoice Item",
			filters={
				"item_code": item_code,
				"rate": [">", 0]
			},
			fields=["rate"],
			order_by="creation desc",
			limit=1
		)

		if purchase_price:
			return {
				"success": True,
				"rate": purchase_price[0].rate,
				"source": "Purchase Invoice"
			}
		
		return {
			"success": True,
			"rate": 0,
			"source": "No data found"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur API taux valorisation: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def get_customer_mobile(customer: str) -> dict[str, Any]:
	"""API endpoint pour récupérer le mobile d'un client.

	Args:
		customer: Nom/ID du client.

	Returns:
		dict[str, Any]: Résultat avec success et mobile.

	Note:
		- Crée une instance temporaire pour réutiliser la logique
		- Délègue à SMSPricingCampaign.get_customer_mobile()
	"""
	try:
		# Créer une instance temporaire pour utiliser la méthode
		temp_campaign = SMSPricingCampaign()
		mobile = temp_campaign.get_customer_mobile(customer)
		
		return {
			"success": True,
			"mobile": mobile
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur API mobile client: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

def calculate_campaign_roi(campaign_name: str) -> dict[str, float] | None:
	"""Calcule le ROI d'une campagne SMS.

	Args:
		campaign_name: Nom/ID de la campagne.

	Returns:
		dict[str, float] | None: ROI avec roi_percent, revenue, cost, profit.
			Retourne None en cas d'erreur.

	Note:
		- ROI % = ((revenue - cost) / cost) × 100
		- Retourne 0 si cost=0
		- Les erreurs sont loggées et retournent None
	"""
	try:
		campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
		
		# Coûts
		sms_cost = campaign.total_sms_cost or 0
		
		# Revenus potentiels
		revenue = campaign.estimated_revenue or 0
		
		# ROI
		if sms_cost > 0:
			roi = ((revenue - sms_cost) / sms_cost) * 100
		else:
			roi = 0
		
		return {
			"roi_percent": roi,
			"revenue": revenue,
			"cost": sms_cost,
			"profit": revenue - sms_cost
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calcul ROI: {e}")
		return None

# Fonctions de validation pour l'installation

def validate_campaign(doc: Any, method: str) -> None:
	"""Validation lors de la soumission d'une campagne.

	Hook appelé lors du submit du document.

	Args:
		doc: Document SMSPricingCampaign.
		method: Nom de la méthode (e.g., "on_submit").

	Raises:
		frappe.ValidationError: Si pricing_items vide.
		frappe.ValidationError: Si valuation_rate manquant.
		frappe.ValidationError: Si OVH SMS non activé.
	"""
	if not doc.pricing_items:
		frappe.throw(_("Aucun article configuré"))
	
	# Vérifier que tous les articles ont un taux de valorisation
	for item in doc.pricing_items:
		if not item.valuation_rate or item.valuation_rate <= 0:
			frappe.throw(_("Taux de valorisation manquant pour {0}").format(item.item_name or item.item_code))
	
	# Vérifier l'intégration OVH SMS
	sms_settings = frappe.get_single('OVH SMS Settings')
	if not sms_settings.enabled:
		frappe.throw(_("OVH SMS Integration doit être activé"))

def on_campaign_submit(doc: Any, method: str) -> None:
	"""Actions lors de la soumission d'une campagne.

	Hook appelé après submit réussi.

	Args:
		doc: Document SMSPricingCampaign.
		method: Nom de la méthode (e.g., "on_submit").

	Note:
		- Met le statut à "Prêt"
		- Commit la transaction
		- Affiche un message de succès
	"""
	# Marquer comme prêt
	doc.db_set('status', 'Prêt')
	frappe.db.commit()
	
	frappe.msgprint(_("Campagne soumise avec succès. Vous pouvez maintenant envoyer les SMS."))

# Hooks pour les événements de documents
def validate_campaign_hook(doc: Any, method: str) -> None:
	"""Hook de validation.

	Wrapper pour validate_campaign().

	Args:
		doc: Document SMSPricingCampaign.
		method: Nom de la méthode.
	"""
	validate_campaign(doc, method)

def on_campaign_submit_hook(doc: Any, method: str) -> None:
	"""Hook de soumission.

	Wrapper pour on_campaign_submit().

	Args:
		doc: Document SMSPricingCampaign.
		method: Nom de la méthode.
	"""
	on_campaign_submit(doc, method)