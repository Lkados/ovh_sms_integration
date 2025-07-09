# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class SMSPricingItem(Document):
	def validate(self):
		"""Validation des lignes de tarification"""
		self.validate_customer_mobile()
		self.validate_pricing()
		self.calculate_totals()

	def validate_customer_mobile(self):
		"""Valide et formate le numéro mobile du client"""
		if self.customer_mobile:
			# Formatage automatique du numéro
			formatted_mobile = self.format_phone_number(self.customer_mobile)
			if formatted_mobile != self.customer_mobile:
				self.customer_mobile = formatted_mobile

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

	def validate_pricing(self):
		"""Valide la tarification"""
		if self.valuation_rate and self.valuation_rate < 0:
			frappe.throw(_("Le taux de valorisation ne peut pas être négatif"))
		
		if self.margin_amount_eur and self.margin_amount_eur < 0:
			frappe.throw(_("La marge ne peut pas être négative"))
		
		if self.qty and self.qty <= 0:
			frappe.throw(_("La quantité doit être positive"))

	def calculate_totals(self):
		"""Calcule les totaux de la ligne avec la nouvelle logique (taux valorisation + marge euros)"""
		if not self.valuation_rate or not self.qty:
			return
		
		try:
			# Prix final = Taux de valorisation + Marge en euros
			self.final_price = (self.valuation_rate or 0) + (self.margin_amount_eur or 0)
			
			# Montant total = Prix final × Quantité
			self.amount = self.final_price * (self.qty or 1)
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul ligne tarification: {e}")
			# Valeurs par défaut en cas d'erreur
			self.final_price = self.valuation_rate or 0
			self.amount = (self.valuation_rate or 0) * (self.qty or 1)

	def get_item_valuation_rate(self, item_code):
		"""Récupère le taux de valorisation le plus récent d'un article"""
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
			
			# Méthode 2: Prix standard de l'article si pas de valorisation
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
			frappe.log_error(f"Erreur récupération taux valorisation {item_code}: {e}")
			return 0

	def on_change(self):
		"""Appelé lors de changements dans le formulaire"""
		# Recalcul automatique si les valeurs changent
		if self.valuation_rate or self.margin_amount_eur or self.qty:
			self.calculate_totals()

	def get_margin_percentage(self):
		"""Calcule le pourcentage de marge pour information (lecture seule)"""
		if self.valuation_rate and self.valuation_rate > 0:
			margin_percent = (self.margin_amount_eur or 0) / self.valuation_rate * 100
			return round(margin_percent, 2)
		return 0

	def get_total_margin_amount(self):
		"""Calcule le montant total de marge pour cette ligne"""
		return (self.margin_amount_eur or 0) * (self.qty or 1)

	def validate_eur_currency(self):
		"""S'assure que la devise est en EUR"""
		if self.currency != "EUR":
			frappe.msgprint(_("Attention: La devise doit être EUR pour les campagnes SMS"))
			self.currency = "EUR"