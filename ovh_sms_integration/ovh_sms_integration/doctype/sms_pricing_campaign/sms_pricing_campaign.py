# -*- coding: utf-8 -*-
"""SMS Pricing Campaign doctype.

Ce module gère les campagnes de tarification SMS pour les clients.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from jinja2 import Template


class SMSPricingCampaign(Document):
    """DocType de campagne de tarification SMS.

    Attributes:
        campaign_name (str): Nom de la campagne
        pricing_items (list): Lignes de tarification
        message_template (str): Template Jinja2 du message
        status (str): Statut de la campagne
    """

    def validate(self) -> None:
        """Valide les données de la campagne avant sauvegarde."""
        if not self.pricing_items:
            frappe.throw(_("Veuillez ajouter au moins un article et client"))

        for item in self.pricing_items:
            self.validate_pricing_item(item)

        self.calculate_totals()
        self.update_status()

    def before_save(self) -> None:
        """Actions avant sauvegarde."""
        self.calculate_totals()

    def validate_pricing_item(self, item: Any) -> None:
        """Valide une ligne de tarification.

        Args:
            item: Ligne de tarification (child table row).
        """
        if not item.customer:
            frappe.throw(_("Client requis dans ligne {0}").format(item.idx))

        if not item.item_code:
            frappe.throw(_("Article requis dans ligne {0}").format(item.idx))

        if not item.customer_mobile:
            mobile = self._get_customer_mobile(item.customer)
            if mobile:
                item.customer_mobile = mobile
            else:
                frappe.throw(
                    _("Numéro mobile requis pour le client {0}").format(item.customer)
                )

        if not item.valuation_rate or item.valuation_rate <= 0:
            frappe.throw(
                _("Taux de valorisation requis pour {0}").format(
                    item.item_name or item.item_code
                )
            )

        if item.margin_amount_eur and item.margin_amount_eur < 0:
            frappe.throw(
                _("La marge ne peut pas être négative pour {0}").format(
                    item.item_name or item.item_code
                )
            )

        item.currency = "EUR"
        self.calculate_item_pricing(item)

    def _get_customer_mobile(self, customer_name: str) -> str | None:
        """Récupère le numéro mobile d'un client.

        Args:
            customer_name: Nom/ID du client.

        Returns:
            str | None: Numéro mobile formaté, ou None si non trouvé.
        """
        from ovh_sms_integration.utils.phone import get_customer_mobile_number

        try:
            customer = frappe.get_doc("Customer", customer_name)
            return get_customer_mobile_number(customer)
        except Exception as e:
            frappe.log_error(f"Erreur récupération mobile client {customer_name}: {e}")
            return None

    def calculate_item_pricing(self, item: Any) -> None:
        """Calcule le prix avec marge pour un article.

        Args:
            item: Ligne de tarification (child table row).
        """
        try:
            item.final_price = (item.valuation_rate or 0) + (
                item.margin_amount_eur or 0
            )
            item.amount = item.final_price * (item.qty or 1)
        except Exception as e:
            frappe.log_error(f"Erreur calcul prix article: {e}")
            item.final_price = item.valuation_rate or 0
            item.amount = item.final_price * (item.qty or 1)

    def calculate_totals(self) -> None:
        """Calcule les totaux et statistiques de la campagne."""
        try:
            if not self.pricing_items:
                return

            total_items = len(self.pricing_items)
            unique_customers: set[str] = set()
            total_amount = 0.0
            total_margin = 0.0
            total_valuation = 0.0
            sms_cost = 0.10

            for item in self.pricing_items:
                if item.customer:
                    unique_customers.add(item.customer)
                total_amount += item.amount or 0
                total_margin += (item.margin_amount_eur or 0) * (item.qty or 1)
                total_valuation += (item.valuation_rate or 0) * (item.qty or 1)

            self.total_items = total_items
            self.total_customers = len(unique_customers)
            self.total_sms_cost = self.total_customers * sms_cost
            self.estimated_revenue = total_amount
            self.profit_potential = total_margin

            if total_valuation > 0:
                self.average_margin_percent = (total_margin / total_valuation) * 100
            else:
                self.average_margin_percent = 0

        except Exception as e:
            frappe.log_error(f"Erreur calcul totaux campagne: {e}")

    def update_status(self) -> None:
        """Met à jour le statut de la campagne selon les envois."""
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
        """
        if not self.pricing_items:
            return False

        return all(
            item.customer_mobile and item.final_price for item in self.pricing_items
        )

    def format_sms_message(self, item: Any) -> str:
        """Formate le message SMS pour un client/article.

        Args:
            item: Ligne de tarification (child table row).

        Returns:
            str: Message SMS formaté.
        """
        try:
            template = (
                self.sms_template
                or "Bonjour {{customer_name}}, nous vous proposons "
                "{{item_name}} au prix de {{final_price}}€."
            )

            context = {
                "customer_name": item.customer_name or item.customer,
                "item_name": item.item_name or item.item_code,
                "item_code": item.item_code,
                "final_price": f"{item.final_price or 0:.2f}",
                "amount": f"{item.amount or 0:.2f}",
                "currency": "EUR",
                "valuation_rate": f"{item.valuation_rate or 0:.2f}",
                "margin_eur": f"{item.margin_amount_eur or 0:.2f}",
                "qty": item.qty or 1,
                "company": self.company
                or frappe.defaults.get_user_default("Company")
                or "",
                "campaign_title": self.title or "",
            }

            template_obj = Template(template)
            return template_obj.render(**context)

        except Exception as e:
            frappe.log_error(f"Erreur formatage message SMS: {e}")
            return f"Offre {item.item_name} à {item.final_price}€ pour {item.customer_name}"

    def send_sms_to_item(self, item: Any) -> dict[str, Any]:
        """Envoie un SMS pour une ligne spécifique.

        Args:
            item: Ligne de tarification (child table row).

        Returns:
            dict[str, Any]: Résultat avec success et message.
        """
        try:
            if item.sms_sent:
                return {"success": False, "message": _("SMS déjà envoyé")}

            if not item.customer_mobile:
                return {"success": False, "message": _("Numéro mobile manquant")}

            message = self.format_sms_message(item)

            sms_settings = frappe.get_single("OVH SMS Settings")
            if not sms_settings.enabled:
                return {"success": False, "message": _("OVH SMS non activé")}

            result = sms_settings.send_sms(message, item.customer_mobile)

            if result and result.get("success"):
                item.sms_sent = 1
                item.sms_status = "Envoyé"
                return {"success": True, "message": _("SMS envoyé avec succès")}
            else:
                item.sms_status = "Échoué"
                error_msg = (
                    result.get("message", "Erreur inconnue")
                    if result
                    else "Pas de réponse"
                )
                return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"Erreur envoi SMS: {str(e)}"
            item.sms_status = "Échoué"
            frappe.log_error(error_msg)
            return {"success": False, "message": error_msg}

    def send_all_sms(self) -> dict[str, Any]:
        """Envoie tous les SMS de la campagne.

        Returns:
            dict[str, Any]: Statistiques d'envoi.
        """
        results: dict[str, Any] = {"sent": 0, "failed": 0, "details": []}

        try:
            for item in self.pricing_items:
                if item.selected_for_sending and not item.sms_sent:
                    result = self.send_sms_to_item(item)

                    if result["success"]:
                        results["sent"] += 1
                    else:
                        results["failed"] += 1

                    results["details"].append(
                        {
                            "customer": item.customer_name or item.customer,
                            "item": item.item_name or item.item_code,
                            "success": result["success"],
                            "message": result["message"],
                        }
                    )

            self.update_sending_statistics(results)
            self.save()

            return results

        except Exception as e:
            frappe.log_error(f"Erreur envoi campagne SMS: {e}")
            return {"sent": 0, "failed": len(self.pricing_items), "error": str(e)}

    def update_sending_statistics(self, results: dict[str, Any]) -> None:
        """Met à jour les statistiques d'envoi.

        Args:
            results: Dict avec sent et failed counts.
        """
        try:
            self.sms_sent_count = (self.sms_sent_count or 0) + results["sent"]
            self.sms_failed_count = (self.sms_failed_count or 0) + results["failed"]
            self.last_sent_time = datetime.now()
            self.update_status()
        except Exception as e:
            frappe.log_error(f"Erreur mise à jour statistiques: {e}")

    def get_preview_messages(self) -> list[dict[str, Any]]:
        """Génère un aperçu des messages pour quelques clients.

        Returns:
            list[dict[str, Any]]: Liste de previews.
        """
        previews: list[dict[str, Any]] = []

        try:
            selected_items = [
                item for item in self.pricing_items if item.selected_for_sending
            ][:3]

            for item in selected_items:
                message = self.format_sms_message(item)
                previews.append(
                    {
                        "customer": item.customer_name or item.customer,
                        "mobile": item.customer_mobile,
                        "item": item.item_name or item.item_code,
                        "price": item.final_price,
                        "valuation": item.valuation_rate,
                        "margin": item.margin_amount_eur,
                        "message": message,
                    }
                )

            return previews

        except Exception as e:
            frappe.log_error(f"Erreur génération aperçu: {e}")
            return []

    def get_item_valuation_rate_internal(self, item_code: str) -> float:
        """Récupère le taux de valorisation d'un article.

        Args:
            item_code: Code de l'article.

        Returns:
            float: Taux de valorisation.
        """
        try:
            valuation = frappe.get_all(
                "Stock Ledger Entry",
                filters={"item_code": item_code, "valuation_rate": [">", 0]},
                fields=["valuation_rate"],
                order_by="posting_date desc, posting_time desc",
                limit=1,
            )

            if valuation:
                return valuation[0].valuation_rate

            item_doc = frappe.get_doc("Item", item_code)
            if hasattr(item_doc, "standard_rate") and item_doc.standard_rate:
                return item_doc.standard_rate

            purchase_price = frappe.get_all(
                "Purchase Invoice Item",
                filters={"item_code": item_code, "rate": [">", 0]},
                fields=["rate"],
                order_by="creation desc",
                limit=1,
            )

            if purchase_price:
                return purchase_price[0].rate

            return 0

        except Exception as e:
            frappe.log_error(
                f"Erreur récupération taux valorisation {item_code}: {e}"
            )
            return 0


# Hooks pour les événements de documents


def validate_campaign(doc: Any, method: str) -> None:
    """Validation lors de la soumission d'une campagne.

    Args:
        doc: Document SMSPricingCampaign.
        method: Nom de la méthode.
    """
    if not doc.pricing_items:
        frappe.throw(_("Aucun article configuré"))

    for item in doc.pricing_items:
        if not item.valuation_rate or item.valuation_rate <= 0:
            frappe.throw(
                _("Taux de valorisation manquant pour {0}").format(
                    item.item_name or item.item_code
                )
            )

    sms_settings = frappe.get_single("OVH SMS Settings")
    if not sms_settings.enabled:
        frappe.throw(_("OVH SMS Integration doit être activé"))


def on_campaign_submit(doc: Any, method: str) -> None:
    """Actions lors de la soumission d'une campagne.

    Args:
        doc: Document SMSPricingCampaign.
        method: Nom de la méthode.
    """
    doc.db_set("status", "Prêt")
    frappe.db.commit()

    frappe.msgprint(
        _("Campagne soumise avec succès. Vous pouvez maintenant envoyer les SMS.")
    )
