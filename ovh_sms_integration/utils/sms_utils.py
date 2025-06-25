# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import json
import re
from datetime import datetime

def get_ovh_sms_settings():
    """Récupère les paramètres OVH SMS"""
    settings = frappe.get_single('OVH SMS Settings')
    if not settings.enabled:
        return None
    return settings

def send_sms(message, receiver, sender=None, context=None):
    """Fonction principale d'envoi SMS"""
    settings = get_ovh_sms_settings()
    if not settings:
        frappe.log_error("OVH SMS non configuré")
        return None
    
    try:
        # Formatage du message avec le contexte
        if context:
            message = format_message_template(message, context)
        
        # Validation du numéro
        receiver = validate_phone_number(receiver)
        
        # Envoi du SMS
        result = settings.send_sms(message, receiver, sender)
        return result
        
    except Exception as e:
        frappe.log_error(f"Erreur envoi SMS: {str(e)}")
        return None

def format_message_template(template, context):
    """Formate un template de message avec les données du contexte"""
    if not template or not context:
        return template
    
    try:
        # Utilise le système de templates Jinja2 de Frappe
        from jinja2 import Template
        
        # Sécurisation des données
        safe_context = {}
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                safe_context[key] = value
            elif hasattr(value, 'strftime'):  # datetime
                safe_context[key] = value.strftime('%d/%m/%Y %H:%M')
            else:
                safe_context[key] = str(value)
        
        template_obj = Template(template)
        return template_obj.render(**safe_context)
        
    except Exception as e:
        frappe.log_error(f"Erreur formatage template: {str(e)}")
        return template

def validate_phone_number(phone):
    """Valide et formate un numéro de téléphone"""
    if not phone:
        return None
    
    # Nettoyage du numéro
    phone = re.sub(r'[^\d+]', '', str(phone))
    
    # Format français
    if phone.startswith('0'):
        phone = '+33' + phone[1:]
    elif not phone.startswith('+'):
        phone = '+33' + phone
    
    # Validation basique
    if not re.match(r'^\+\d{10,15}$', phone):
        raise ValueError(f"Numéro de téléphone invalide: {phone}")
    
    return phone

def get_contact_mobile(doc):
    """Récupère le numéro de mobile d'un document"""
    mobile_fields = ['mobile_no', 'phone_no', 'contact_mobile', 'mobile', 'phone']
    
    for field in mobile_fields:
        if hasattr(doc, field) and doc.get(field):
            return doc.get(field)
    
    # Recherche dans les contacts liés
    if hasattr(doc, 'contact_person') and doc.contact_person:
        contact = frappe.get_doc('Contact', doc.contact_person)
        for field in mobile_fields:
            if hasattr(contact, field) and contact.get(field):
                return contact.get(field)
    
    return None

# Handlers pour les événements de documents
def on_document_update(doc, method):
    """Handler générique pour les mises à jour de documents"""
    pass

def on_document_submit(doc, method):
    """Handler générique pour les soumissions de documents"""
    pass

def on_document_cancel(doc, method):
    """Handler générique pour les annulations de documents"""
    pass

def send_sales_order_sms(doc, method):
    """Envoie un SMS lors de la soumission d'une commande"""
    settings = get_ovh_sms_settings()
    if not settings or not settings.enable_sales_order_sms:
        return
    
    mobile = get_contact_mobile(doc)
    if not mobile:
        return
    
    template = settings.sales_order_template
    context = {
        'name': doc.name,
        'customer': doc.customer,
        'grand_total': doc.grand_total,
        'currency': doc.currency,
        'transaction_date': doc.transaction_date
    }
    
    send_sms(template, mobile, context=context)

def send_payment_confirmation_sms(doc, method):
    """Envoie un SMS lors de la confirmation d'un paiement"""
    settings = get_ovh_sms_settings()
    if not settings or not settings.enable_payment_sms:
        return
    
    mobile = get_contact_mobile(doc)
    if not mobile:
        return
    
    template = settings.payment_template
    context = {
        'name': doc.name,
        'paid_amount': doc.paid_amount,
        'currency': doc.paid_from_account_currency,
        'posting_date': doc.posting_date
    }
    
    send_sms(template, mobile, context=context)

def send_delivery_sms(doc, method):
    """Envoie un SMS lors de l'expédition"""
    settings = get_ovh_sms_settings()
    if not settings or not settings.enable_delivery_sms:
        return
    
    mobile = get_contact_mobile(doc)
    if not mobile:
        return
    
    template = settings.delivery_template
    context = {
        'name': doc.name,
        'customer': doc.customer,
        'posting_date': doc.posting_date
    }
    
    send_sms(template, mobile, context=context)

def send_purchase_order_sms(doc, method):
    """Envoie un SMS lors de la soumission d'une commande fournisseur"""
    settings = get_ovh_sms_settings()
    if not settings or not settings.enable_purchase_order_sms:
        return
    
    mobile = get_contact_mobile(doc)
    if not mobile:
        return
    
    template = settings.purchase_order_template
    context = {
        'name': doc.name,
        'supplier': doc.supplier,
        'supplier_name': doc.supplier_name,
        'grand_total': doc.grand_total,
        'currency': doc.currency,
        'transaction_date': doc.transaction_date
    }
    
    send_sms(template, mobile, context=context)

def send_daily_reminders():
    """Envoie les rappels quotidiens"""
    # Implémentation des rappels quotidiens
    pass

def send_weekly_reports():
    """Envoie les rapports hebdomadaires"""
    # Implémentation des rapports hebdomadaires
    pass

@frappe.whitelist()
def test_ovh_connection():
    """Test la connexion OVH"""
    settings = get_ovh_sms_settings()
    if not settings:
        return {"success": False, "message": "OVH SMS non configuré"}
    
    return settings.test_connection()

@frappe.whitelist()
def send_manual_sms(message, receivers, sender=None):
    """Envoie un SMS manuel"""
    if isinstance(receivers, str):
        receivers = [receivers]
    
    results = []
    for receiver in receivers:
        result = send_sms(message, receiver, sender)
        results.append({
            "receiver": receiver,
            "success": result is not None,
            "result": result
        })
    
    return results

@frappe.whitelist()
def get_sms_balance():
    """Récupère le solde SMS"""
    settings = get_ovh_sms_settings()
    if not settings:
        return None
    
    return settings.get_sms_balance()

def format_sms_message(template, doc):
    """Fonction Jinja pour formater les messages SMS"""
    if not template or not doc:
        return template
    
    context = doc.as_dict()
    return format_message_template(template, context)