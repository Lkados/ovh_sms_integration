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
		if self.base_rate and self.base_rate < 0:
			frappe.throw(_("Le taux de base ne peut pas être négatif"))
		
		if self.margin_type == "Percentage" and self.margin_percent:
			if self.margin_percent < -100:
				frappe.throw(_("La marge ne peut pas être inférieure à -100%"))
		
		if self.qty and self.qty <= 0:
			frappe.throw(_("La quantité doit être positive"))

	def calculate_totals(self):
		"""Calcule les totaux de la ligne"""
		if not self.base_rate or not self.qty:
			return
		
		try:
			# Montant de base
			base_amount = self.base_rate * self.qty
			
			# Calcul de la marge
			if self.margin_type == "Percentage":
				margin_value = base_amount * (self.margin_percent or 0) / 100
			else:  # Amount
				margin_value = (self.margin_amount or 0) * self.qty
			
			# Prix final
			self.rate_with_margin = self.base_rate + (margin_value / self.qty)
			self.amount = self.rate_with_margin * self.qty
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul ligne tarification: {e}")
			# Valeurs par défaut en cas d'erreur
			self.rate_with_margin = self.base_rate or 0
			self.amount = (self.base_rate or 0) * (self.qty or 1)