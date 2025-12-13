# -*- coding: utf-8 -*-
"""
Commandes CLI pour la gestion d'OVH SMS Integration.

Usage:
    bench execute ovh_sms_integration.cli_commands.function_name --args '{"arg1": "value1"}'
"""

from __future__ import unicode_literals

import json
from datetime import datetime, timedelta

import click
import frappe


def setup_sms_integration() -> None:
    """Configure initialement le système SMS complet."""
    try:
        print("🚀 Configuration OVH SMS Integration...")

        # 1. Vérification des prérequis
        print("1. Vérification des prérequis...")
        if not frappe.db.exists("DocType", "OVH SMS Settings"):
            print("❌ DocType OVH SMS Settings manquant")
            return

        if not frappe.db.exists("DocType", "SMS Event Reminder"):
            print("❌ DocType SMS Event Reminder manquant")
            return

        print("✅ DocTypes présents")

        # 2. Configuration par défaut OVH SMS
        print("2. Configuration OVH SMS Settings...")
        sms_settings = frappe.get_single("OVH SMS Settings")

        if not sms_settings.default_sender:
            sms_settings.db_set("default_sender", "ERPNext")

        if not sms_settings.auto_detect_service:
            sms_settings.db_set("auto_detect_service", 1)

        print("✅ OVH SMS Settings configuré")

        # 3. Configuration par défaut Rappels
        print("3. Configuration SMS Event Reminder...")
        reminder_settings = frappe.get_single("SMS Event Reminder")

        if not reminder_settings.event_type_filter:
            reminder_settings.db_set("event_type_filter", "entretien")

        if not reminder_settings.reminder_hours_before:
            reminder_settings.db_set("reminder_hours_before", 24)

        if not reminder_settings.reminder_message_template:
            template = (
                "Rappel : Vous avez un rendez-vous {{subject}} prévu le "
                "{{start_date}} à {{start_time}}. Merci de vous présenter à l'heure."
            )
            reminder_settings.db_set("reminder_message_template", template)

        print("✅ SMS Event Reminder configuré")

        # 4. Activation des modules
        print("4. Activation des modules...")
        reminder_settings.db_set("enabled", 1)
        print("✅ Rappels activés")

        frappe.db.commit()
        print("\n🎉 Configuration terminée avec succès !")

    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        frappe.log_error(f"Erreur setup SMS: {e}")


def test_sms_connection() -> None:
    """Teste la connexion OVH SMS."""
    try:
        print("📡 Test de connexion OVH SMS...")

        sms_settings = frappe.get_single("OVH SMS Settings")

        if not sms_settings.enabled:
            print("❌ OVH SMS non activé")
            return

        result = sms_settings.test_connection()

        if result.get("success"):
            print("✅ Connexion réussie !")
            print(f"Details: {result.get('message')}")
        else:
            print("❌ Connexion échouée")
            print(f"Erreur: {result.get('message')}")

    except Exception as e:
        print(f"❌ Erreur test connexion: {e}")


def send_test_sms(mobile: str | None = None, message: str | None = None) -> None:
    """Envoie un SMS de test."""
    try:
        if not mobile:
            mobile = input("📱 Numéro de mobile (ex: +33123456789): ")

        if not message:
            message = f"Test SMS ERPNext - {datetime.now().strftime('%H:%M')}"

        print(f"📤 Envoi SMS de test vers {mobile}...")

        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            send_test_sms,
        )

        result = send_test_sms(mobile, message)

        if result.get("success"):
            print("✅ SMS envoyé avec succès !")
            print(f"Détails: {result.get('message')}")
        else:
            print("❌ Envoi échoué")
            print(f"Erreur: {result.get('message')}")

    except Exception as e:
        print(f"❌ Erreur envoi SMS: {e}")


def check_pending_reminders() -> None:
    """Vérifie les rappels en attente."""
    try:
        print("⏰ Vérification des rappels en attente...")

        from ovh_sms_integration.utils.sms_utils import get_events_requiring_reminders

        events = get_events_requiring_reminders()

        if events:
            print(f"📅 {len(events)} événement(s) nécessitent un rappel:")
            for event in events:
                start_date = (
                    event.starts_on.strftime("%d/%m/%Y %H:%M")
                    if event.starts_on
                    else "N/A"
                )
                print(f"  - {event.subject} ({start_date})")
        else:
            print("✅ Aucun rappel en attente")

    except Exception as e:
        print(f"❌ Erreur vérification rappels: {e}")


def send_reminders_now() -> None:
    """Force l'envoi des rappels maintenant."""
    try:
        print("🚀 Envoi forcé des rappels...")

        from ovh_sms_integration.utils.sms_utils import process_pending_event_reminders

        result = process_pending_event_reminders()

        if result.get("success"):
            print("✅ Rappels traités !")
            print(f"Envoyés: {result.get('sent', 0)}")
            print(f"Échoués: {result.get('failed', 0)}")
        else:
            print("❌ Erreur traitement rappels")
            print(f"Message: {result.get('message')}")

    except Exception as e:
        print(f"❌ Erreur envoi rappels: {e}")


def show_sms_statistics() -> None:
    """Affiche les statistiques SMS."""
    try:
        print("📊 Statistiques SMS")
        print("=" * 40)

        # Statistiques OVH SMS
        sms_settings = frappe.get_single("OVH SMS Settings")
        print("📱 OVH SMS:")
        print(f"  Activé: {'✅' if sms_settings.enabled else '❌'}")
        print(f"  Total envoyés: {sms_settings.total_sms_sent or 0}")
        print(f"  Envoyés aujourd'hui: {sms_settings.sms_sent_today or 0}")
        print(f"  Dernier envoi: {sms_settings.last_sms_sent or 'Jamais'}")

        # Statistiques rappels
        reminder_settings = frappe.get_single("SMS Event Reminder")
        print("\n⏰ Rappels d'événements:")
        print(f"  Activé: {'✅' if reminder_settings.enabled else '❌'}")
        print(f"  Total rappels: {reminder_settings.total_reminders_sent or 0}")
        print(f"  Rappels aujourd'hui: {reminder_settings.reminders_sent_today or 0}")
        print(f"  Échecs: {reminder_settings.failed_reminders_count or 0}")
        print(f"  Dernier rappel: {reminder_settings.last_reminder_sent or 'Jamais'}")

        # Solde SMS
        try:
            from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
                get_account_balance,
            )

            balance = get_account_balance()
            if balance.get("success"):
                print("\n💰 Solde:")
                print(f"  Service: {balance.get('service_name')}")
                print(f"  Crédits: {balance.get('credits')}")
        except Exception:
            print("\n💰 Solde: Non disponible")

    except Exception as e:
        print(f"❌ Erreur récupération statistiques: {e}")


def cleanup_sms_logs() -> None:
    """Nettoie les anciens logs SMS."""
    try:
        print("🧹 Nettoyage des logs SMS...")

        # Suppression des logs de plus de 30 jours
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # Récupérer les logs SMS/OVH/rappel de plus de 30 jours
        old_logs = frappe.get_all(
            "Error Log",
            filters={
                "creation": ["<", thirty_days_ago],
            },
            fields=["name", "error"],
        )

        # Filtrer les logs liés aux SMS
        sms_related_logs = [
            log.name
            for log in old_logs
            if log.error
            and any(
                keyword in log.error.lower() for keyword in ["sms", "ovh", "rappel"]
            )
        ]

        # Supprimer les logs filtrés
        deleted_count = 0
        for log_name in sms_related_logs:
            frappe.delete_doc("Error Log", log_name, ignore_permissions=True)
            deleted_count += 1

        frappe.db.commit()

        print(f"✅ {deleted_count} logs supprimés")

    except Exception as e:
        print(f"❌ Erreur nettoyage logs: {e}")


def reset_sms_counters() -> None:
    """Remet à zéro les compteurs SMS."""
    try:
        print("🔄 Remise à zéro des compteurs...")

        # Reset compteurs OVH SMS
        sms_settings = frappe.get_single("OVH SMS Settings")
        sms_settings.db_set("sms_sent_today", 0)

        # Reset compteurs rappels
        reminder_settings = frappe.get_single("SMS Event Reminder")
        reminder_settings.db_set("reminders_sent_today", 0)

        frappe.db.commit()

        print("✅ Compteurs remis à zéro")

    except Exception as e:
        print(f"❌ Erreur reset compteurs: {e}")


def backup_sms_settings() -> None:
    """Sauvegarde la configuration SMS."""
    try:
        print("💾 Sauvegarde de la configuration SMS...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sms_config_backup_{timestamp}.json"

        # Récupération des paramètres
        sms_settings = frappe.get_single("OVH SMS Settings")
        reminder_settings = frappe.get_single("SMS Event Reminder")

        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "ovh_sms_settings": {
                "enabled": sms_settings.enabled,
                "auto_detect_service": sms_settings.auto_detect_service,
                "default_sender": sms_settings.default_sender,
                "service_name": sms_settings.service_name,
                "enable_sales_order_sms": sms_settings.enable_sales_order_sms,
                "enable_payment_sms": sms_settings.enable_payment_sms,
                "enable_delivery_sms": sms_settings.enable_delivery_sms,
                # Ne pas sauvegarder les secrets
            },
            "reminder_settings": {
                "enabled": reminder_settings.enabled,
                "event_type_filter": reminder_settings.event_type_filter,
                "reminder_hours_before": reminder_settings.reminder_hours_before,
                "enable_multiple_reminders": reminder_settings.enable_multiple_reminders,
                "reminder_times": reminder_settings.reminder_times,
                "send_to_customer_only": reminder_settings.send_to_customer_only,
                "send_to_employee": reminder_settings.send_to_employee,
                "reminder_message_template": reminder_settings.reminder_message_template,
                "customer_template": reminder_settings.customer_template,
                "employee_template": reminder_settings.employee_template,
            },
        }

        # Sauvegarde
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"✅ Configuration sauvegardée: {filename}")

    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")


def create_test_event() -> str | None:
    """Crée un événement de test pour les rappels."""
    try:
        print("📅 Création d'un événement de test...")

        # Paramètres de l'événement
        start_time = datetime.now() + timedelta(
            hours=25
        )  # Dans 25h pour tester les rappels 24h
        end_time = start_time + timedelta(hours=1)

        event = frappe.get_doc(
            {
                "doctype": "Event",
                "subject": "Test entretien SMS automatique",
                "description": "Événement créé pour tester les rappels SMS automatiques",
                "starts_on": start_time,
                "ends_on": end_time,
                "event_type": "Private",
                "all_day": 0,
            }
        )

        event.insert()
        event.submit()

        print(f"✅ Événement créé: {event.name}")
        print(f"   Titre: {event.subject}")
        print(f"   Date: {start_time.strftime('%d/%m/%Y %H:%M')}")
        print(
            f"   Rappel prévu vers: {(start_time - timedelta(hours=24)).strftime('%d/%m/%Y %H:%M')}"
        )

        return event.name

    except Exception as e:
        print(f"❌ Erreur création événement: {e}")
        return None


def monitor_scheduler() -> None:
    """Surveille le statut du scheduler."""
    try:
        print("⚙️ Statut du Scheduler")
        print("=" * 30)

        # Vérification statut général
        scheduler_disabled = frappe.conf.get("pause_scheduler", False)

        if scheduler_disabled:
            print("❌ Scheduler désactivé")
            print("💡 Pour l'activer: bench --site [site] set-config pause_scheduler 0")
        else:
            print("✅ Scheduler activé")

        # Vérification des tâches spécifiques
        print("\n📋 Tâches SMS configurées:")

        tasks = [
            ("Toutes les exécutions", "process_event_reminders"),
            ("Horaire", "check_event_reminders_hourly"),
            ("Quotidien", "reset_daily_counters"),
            ("Hebdomadaire", "cleanup_old_reminder_logs"),
        ]

        for frequency, task_name in tasks:
            print(f"  {frequency}: {task_name}")

        # Dernière exécution
        reminder_settings = frappe.get_single("SMS Event Reminder")
        if reminder_settings.last_check_time:
            last_check = reminder_settings.last_check_time
            hours_ago = (datetime.now() - last_check).total_seconds() / 3600
            print(f"\n🕒 Dernière vérification: il y a {hours_ago:.1f}h")
        else:
            print("\n🕒 Dernière vérification: Jamais")

    except Exception as e:
        print(f"❌ Erreur monitoring scheduler: {e}")


def run_health_check_cli() -> None:
    """Exécute la vérification de santé depuis CLI."""
    try:
        from ovh_sms_integration.health_check import run_health_check

        run_health_check()
    except ImportError:
        print("❌ Module health_check non trouvé")
    except Exception as e:
        print(f"❌ Erreur health check: {e}")


# Fonctions utilitaires CLI


@click.command()
@click.option("--action", prompt="Action à exécuter", help="Action à exécuter")
def sms_cli(action: str) -> None:
    """Interface CLI principale pour OVH SMS Integration."""

    actions = {
        "setup": setup_sms_integration,
        "test-connection": test_sms_connection,
        "test-sms": send_test_sms,
        "check-reminders": check_pending_reminders,
        "send-reminders": send_reminders_now,
        "stats": show_sms_statistics,
        "cleanup": cleanup_sms_logs,
        "reset-counters": reset_sms_counters,
        "backup": backup_sms_settings,
        "create-test-event": create_test_event,
        "monitor-scheduler": monitor_scheduler,
        "health-check": run_health_check_cli,
    }

    if action in actions:
        print(f"🚀 Exécution: {action}")
        actions[action]()
    else:
        print("❌ Action inconnue")
        print("Actions disponibles:")
        for key in actions.keys():
            print(f"  - {key}")


# Commandes spécifiques pour l'utilisation avec bench execute


def execute_setup() -> None:
    """Execute setup_sms_integration via bench execute."""
    setup_sms_integration()


def execute_test_connection() -> None:
    """Execute test_sms_connection via bench execute."""
    test_sms_connection()


def execute_check_reminders() -> None:
    """Execute check_pending_reminders via bench execute."""
    check_pending_reminders()


def execute_send_reminders() -> None:
    """Execute send_reminders_now via bench execute."""
    send_reminders_now()


def execute_stats() -> None:
    """Execute show_sms_statistics via bench execute."""
    show_sms_statistics()


def execute_health_check() -> None:
    """Execute run_health_check_cli via bench execute."""
    run_health_check_cli()


if __name__ == "__main__":
    sms_cli()
