# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime
import json
from jinja2 import Template

class SMSPricingCampaign(Document):
	def validate(self):
		"""Validation des données de la campagne"""
		if not self.pricing_items:
			frappe.throw(_("Veuillez ajouter au moins un article et client"))
		
		# Validation des lignes
		for item in self.pricing_items:
			self.validate_pricing_item(item)
		
		# Calcul des totaux
		self.calculate_totals()
		
		# Mise à jour du statut
		self.update_status()

	def before_save(self):
		"""Actions avant sauvegarde"""
		self.calculate_totals()

	def validate_pricing_item(self, item):
		"""Valide une ligne de tarification"""
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

	def get_customer_mobile(self, customer_name):
		"""Récupère le numéro mobile d'un client"""
		try:
			customer = frappe.get_doc("Customer", customer_name)
			
			# Vérifier le champ mobile du customer
			if hasattr(customer, 'mobile_no') and customer.mobile_no:
				return self.format_phone_number(customer.mobile_no)
			
			# Chercher dans les contacts liés
			contacts = frappe.db.sql("""
				SELECT mobile_no, phone
				FROM `tabContact`
				WHERE name IN (
					SELECT parent FROM `tabDynamic Link`
					WHERE link_doctype = 'Customer' AND link_name = %s
				)
				AND (mobile_no IS NOT NULL OR phone IS NOT NULL)
				LIMIT 1
			""", customer_name, as_dict=True)
			
			if contacts:
				mobile = contacts[0].mobile_no or contacts[0].phone
				return self.format_phone_number(mobile)
				
		except Exception as e:
			frappe.log_error(f"Erreur récupération mobile client {customer_name}: {e}")
		
		return None

	def format_phone_number(self, phone):
		"""Formate un numéro de téléphone français"""
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

	def calculate_item_pricing(self, item):
		"""Calcule le prix avec marge pour un article - NOUVELLE LOGIQUE"""
		try:
			# Nouvelle logique: Prix final = Taux de valorisation + Marge en euros
			item.final_price = (item.valuation_rate or 0) + (item.margin_amount_eur or 0)
			
			# Montant total = Prix final × Quantité
			item.amount = item.final_price * (item.qty or 1)
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul prix article: {e}")
			item.final_price = item.valuation_rate or 0
			item.amount = item.final_price * (item.qty or 1)

	def calculate_totals(self):
		"""Calcule les totaux de la campagne"""
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

	def update_status(self):
		"""Met à jour le statut de la campagne"""
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

	def validate_ready_to_send(self):
		"""Vérifie si la campagne est prête à être envoyée"""
		if not self.pricing_items:
			return False
		
		for item in self.pricing_items:
			if not item.customer_mobile or not item.final_price:
				return False
		
		return True

	def format_sms_message(self, item):
		"""Formate le message SMS pour un client/article"""
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

	def send_sms_to_item(self, item):
		"""Envoie un SMS pour une ligne spécifique"""
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

	def send_all_sms(self):
		"""Envoie tous les SMS de la campagne"""
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

	def update_sending_statistics(self, results):
		"""Met à jour les statistiques d'envoi"""
		try:
			self.sms_sent_count = (self.sms_sent_count or 0) + results["sent"]
			self.sms_failed_count = (self.sms_failed_count or 0) + results["failed"]
			self.last_sent_time = datetime.now()
			
			# Mise à jour du statut
			self.update_status()
			
		except Exception as e:
			frappe.log_error(f"Erreur mise à jour statistiques: {e}")

	def get_preview_messages(self):
		"""Génère un aperçu des messages pour quelques clients"""
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

	def get_item_valuation_rate_internal(self, item_code):
		"""Récupère le taux de valorisation d'un article - méthode interne"""
		try:
			# Méthode 1: Dernière valorisation en stock
			valuation = frappe.db.sql("""
				SELECT valuation_rate
				FROM `tabStock Ledger Entry`
				WHERE item_code = %s
				AND valuation_rate > 0
				ORDER BY posting_date DESC, posting_time DESC
				LIMIT 1
			""", item_code)
			
			if valuation:
				return valuation[0][0]
			
			# Méthode 2: Prix standard de l'article
			item_doc = frappe.get_doc("Item", item_code)
			if hasattr(item_doc, 'standard_rate') and item_doc.standard_rate:
				return item_doc.standard_rate
			
			# Méthode 3: Dernier prix d'achat
			purchase_price = frappe.db.sql("""
				SELECT rate
				FROM `tabPurchase Invoice Item`
				WHERE item_code = %s
				AND rate > 0
				ORDER BY creation DESC
				LIMIT 1
			""", item_code)
			
			if purchase_price:
				return purchase_price[0][0]
			
			return 0
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération taux valorisation interne {item_code}: {e}")
			return 0


# === MÉTHODES GLOBALES POUR L'API ===

@frappe.whitelist()
def send_all_sms(campaign_name):
	"""API pour envoyer tous les SMS d'une campagne"""
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
def send_selected_sms(campaign_name):
	"""API pour envoyer les SMS sélectionnés"""
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
def preview_messages(campaign_name):
	"""API pour prévisualiser les messages SMS"""
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
def send_test_sms(campaign_name, test_mobile):
	"""API pour envoyer un SMS de test"""
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
def get_item_valuation_rate(item_code):
	"""API pour récupérer le taux de valorisation d'un article"""
	try:
		# Méthode 1: Dernière valorisation en stock
		valuation = frappe.db.sql("""
			SELECT valuation_rate
			FROM `tabStock Ledger Entry`
			WHERE item_code = %s
			AND valuation_rate > 0
			ORDER BY posting_date DESC, posting_time DESC
			LIMIT 1
		""", item_code)
		
		if valuation:
			return {
				"success": True,
				"rate": valuation[0][0],
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
		
		# Méthode 3: Dernier prix d'achat
		purchase_price = frappe.db.sql("""
			SELECT rate
			FROM `tabPurchase Invoice Item`
			WHERE item_code = %s
			AND rate > 0
			ORDER BY creation DESC
			LIMIT 1
		""", item_code)
		
		if purchase_price:
			return {
				"success": True,
				"rate": purchase_price[0][0],
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
def get_customer_mobile(customer):
	"""API pour récupérer le mobile d'un client"""
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

def calculate_campaign_roi(campaign_name):
	"""Calcule le ROI d'une campagne SMS"""
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

def validate_campaign(doc, method):
	"""Validation lors de la soumission d'une campagne"""
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

def on_campaign_submit(doc, method):
	"""Actions lors de la soumission d'une campagne"""
	# Marquer comme prêt
	doc.db_set('status', 'Prêt')
	frappe.db.commit()
	
	frappe.msgprint(_("Campagne soumise avec succès. Vous pouvez maintenant envoyer les SMS."))

# Hooks pour les événements de documents
def validate_campaign_hook(doc, method):
	"""Hook de validation"""
	validate_campaign(doc, method)

def on_campaign_submit_hook(doc, method):
	"""Hook de soumission"""
	on_campaign_submit(doc, method)