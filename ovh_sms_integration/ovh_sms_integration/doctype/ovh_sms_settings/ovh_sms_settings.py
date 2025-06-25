# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import json
import requests
import hashlib
import time
from datetime import datetime

class OVHSMSSettings(Document):
    def validate(self):
        """Validation des paramètres"""
        if self.enabled:
            self.validate_api_credentials()
            self.validate_templates()
    
    def validate_api_credentials(self):
        """Valide les credentials API OVH"""
        required_fields = ['application_key', 'application_secret', 'consumer_key']
        
        for field in required_fields:
            if not self.get(field):
                frappe.throw(_("Le champ {0} est requis").format(self.meta.get_label(field)))
        
        if not self.auto_detect_service and not self.service_name:
            frappe.throw(_("Le nom du service est requis si la détection automatique est désactivée"))
    
    def validate_templates(self):
        """Valide les templates SMS"""
        templates = [
            'sales_order_template',
            'payment_template', 
            'delivery_template',
            'purchase_order_template'
        ]
        
        for template_field in templates:
            template = self.get(template_field)
            if template and len(template) > 160:
                frappe.msgprint(_("Le template {0} dépasse 160 caractères").format(
                    self.meta.get_label(template_field)
                ), alert=True)
    
    def get_ovh_signature(self, method, url, body, timestamp):
        """Génère la signature OVH"""
        pre_hash = f"{self.application_secret}+{self.consumer_key}+{method}+{url}+{body}+{timestamp}"
        return "$1$" + hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
    
    def get_service_name(self):
        """Récupère le nom du service SMS"""
        if not self.auto_detect_service:
            return self.service_name
        
        # Détection automatique
        timestamp = str(int(time.time()))
        method = "GET"
        url = "https://eu.api.ovh.com/1.0/sms"
        body = ""
        
        signature = self.get_ovh_signature(method, url, body, timestamp)
        
        headers = {
            "X-Ovh-Application": self.application_key,
            "X-Ovh-Consumer": self.consumer_key,
            "X-Ovh-Signature": signature,
            "X-Ovh-Timestamp": timestamp
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.api_timeout or 30)
            response.raise_for_status()
            
            services = response.json()
            if services:
                return services[0]
            else:
                frappe.throw(_("Aucun service SMS trouvé"))
                
        except Exception as e:
            frappe.log_error(f"Erreur récupération service SMS: {str(e)}")
            frappe.throw(_("Impossible de récupérer le service SMS: {0}").format(str(e)))
    
    def send_sms(self, message, receiver, sender=None):
        """Envoie un SMS via l'API OVH"""
        if not self.enabled:
            frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
        
        service_name = self.get_service_name()
        sender = sender or self.default_sender
        
        timestamp = str(int(time.time()))
        method = "POST"
        url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/jobs"
        
        body_data = {
            "message": message,
            "receivers": [receiver] if isinstance(receiver, str) else receiver,
            "sender": sender,
            "senderForResponse": True
        }
        
        body = json.dumps(body_data, separators=(',', ':'))
        signature = self.get_ovh_signature(method, url, body, timestamp)
        
        headers = {
            "X-Ovh-Application": self.application_key,
            "X-Ovh-Consumer": self.consumer_key,
            "X-Ovh-Signature": signature,
            "X-Ovh-Timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        # Headers personnalisés
        if self.custom_headers:
            try:
                custom_headers = json.loads(self.custom_headers)
                headers.update(custom_headers)
            except:
                pass
        
        try:
            response = requests.post(
                url, 
                data=body, 
                headers=headers, 
                timeout=self.api_timeout or 30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Log success
            if self.enable_logging:
                frappe.logger().info(f"SMS envoyé avec succès: {result}")
            
            # Créer un log SMS
            self.create_sms_log(message, receiver, sender, "Success", result)
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # Log error
            frappe.log_error(f"Erreur envoi SMS OVH: {error_msg}")
            
            # Créer un log d'erreur
            self.create_sms_log(message, receiver, sender, "Failed", {"error": error_msg})
            
            # Retry logic
            if hasattr(self, '_retry_count'):
                self._retry_count += 1
            else:
                self._retry_count = 1
            
            if self._retry_count < (self.max_retries or 3):
                time.sleep(2 ** self._retry_count)  # Exponential backoff
                return self.send_sms(message, receiver, sender)
            
            frappe.throw(_("Erreur lors de l'envoi du SMS: {0}").format(error_msg))
    
    def create_sms_log(self, message, receiver, sender, status, response):
        """Crée un log SMS"""
        try:
            log_doc = frappe.get_doc({
                "doctype": "SMS Log",
                "message": message,
                "receiver": receiver,
                "sender": sender,
                "status": status,
                "response": json.dumps(response) if isinstance(response, dict) else str(response),
                "timestamp": datetime.now()
            })
            log_doc.insert(ignore_permissions=True)
            frappe.db.commit()
        except:
            pass  # Ne pas faire échouer l'envoi SMS pour un problème de log
    
    def get_sms_balance(self):
        """Récupère le solde SMS"""
        service_name = self.get_service_name()
        
        timestamp = str(int(time.time()))
        method = "GET"
        url = f"https://eu.api.ovh.com/1.0/sms/{service_name}"
        body = ""
        
        signature = self.get_ovh_signature(method, url, body, timestamp)
        
        headers = {
            "X-Ovh-Application": self.application_key,
            "X-Ovh-Consumer": self.consumer_key,
            "X-Ovh-Signature": signature,
            "X-Ovh-Timestamp": timestamp
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.api_timeout or 30)
            response.raise_for_status()
            
            data = response.json()
            balance = data.get('creditsLeft', 0)
            
            # Mettre à jour le solde
            frappe.db.set_value('OVH SMS Settings', 'OVH SMS Settings', 'sms_balance', balance)
            frappe.db.commit()
            
            return balance
            
        except Exception as e:
            frappe.log_error(f"Erreur récupération solde SMS: {str(e)}")
            return None
    
    def test_connection(self):
        """Test la connexion à l'API OVH"""
        timestamp = str(int(time.time()))
        method = "GET"
        url = "https://eu.api.ovh.com/1.0/me"
        body = ""
        
        signature = self.get_ovh_signature(method, url, body, timestamp)
        
        headers = {
            "X-Ovh-Application": self.application_key,
            "X-Ovh-Consumer": self.consumer_key,
            "X-Ovh-Signature": signature,
            "X-Ovh-Timestamp": timestamp
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.api_timeout or 30)
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "message": f"Connexion réussie - Compte: {data.get('nichandle', 'N/A')}",
                "data": data
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur de connexion: {str(e)}"
            }

# Méthodes pour les boutons
@frappe.whitelist()
def send_test_sms():
    """Envoie un SMS de test"""
    settings = frappe.get_single('OVH SMS Settings')
    
    if not settings.test_mobile:
        frappe.throw(_("Veuillez saisir un numéro de téléphone de test"))
    
    message = settings.test_message or "Test SMS ERPNext-OVH"
    
    try:
        result = settings.send_sms(message, settings.test_mobile)
        
        test_result = {
            "success": True,
            "message": "SMS de test envoyé avec succès",
            "ids": result.get('ids', []),
            "credits": result.get('totalCreditsRemoved', 0),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        frappe.set_value('OVH SMS Settings', 'OVH SMS Settings', 'last_test_result', 
                        json.dumps(test_result, indent=2))
        
        frappe.msgprint(_("SMS de test envoyé avec succès!"), alert=True, indicator='green')
        return test_result
        
    except Exception as e:
        test_result = {
            "success": False,
            "message": f"Erreur lors de l'envoi: {str(e)}",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        frappe.set_value('OVH SMS Settings', 'OVH SMS Settings', 'last_test_result', 
                        json.dumps(test_result, indent=2))
        
        frappe.msgprint(_("Erreur lors de l'envoi du SMS de test: {0}").format(str(e)), 
                       alert=True, indicator='red')
        return test_result

@frappe.whitelist()
def refresh_balance():
    """Actualise le solde SMS"""
    settings = frappe.get_single('OVH SMS Settings')
    
    try:
        balance = settings.get_sms_balance()
        if balance is not None:
            frappe.msgprint(_("Solde SMS actualisé: {0} crédits").format(balance), 
                           alert=True, indicator='green')
        else:
            frappe.msgprint(_("Impossible de récupérer le solde SMS"), 
                           alert=True, indicator='orange')
    except Exception as e:
        frappe.msgprint(_("Erreur lors de la récupération du solde: {0}").format(str(e)), 
                       alert=True, indicator='red')