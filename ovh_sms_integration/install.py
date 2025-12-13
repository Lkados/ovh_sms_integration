# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _


def after_install():
    """Exécuté après l'installation de l'app"""
    try:
        frappe.logger().info(
            "Début installation OVH SMS Integration avec rappels événements"
        )

        # Création des rôles nécessaires
        create_sms_roles()

        # Configuration des permissions par défaut
        setup_default_permissions()

        # Création des paramètres par défaut
        setup_default_settings()

        # Configuration du scheduler
        setup_scheduler_events()

        # Messages de fin d'installation
        show_installation_messages()

        frappe.logger().info("Installation OVH SMS Integration terminée avec succès")

    except Exception as e:
        frappe.log_error(f"Erreur installation OVH SMS Integration: {e}")
        frappe.throw(_("Erreur lors de l'installation: {0}").format(str(e)))


def create_sms_roles():
    """Crée les rôles nécessaires pour la gestion SMS"""
    try:
        roles_to_create = [
            {
                "role_name": "SMS Manager",
                "desk_access": 1,
                "description": "Peut gérer tous les paramètres SMS et envoyer des messages",
            },
            {
                "role_name": "SMS User",
                "desk_access": 1,
                "description": "Peut envoyer des SMS et voir les statistiques de base",
            },
        ]

        for role_data in roles_to_create:
            if not frappe.db.exists("Role", role_data["role_name"]):
                role_doc = frappe.get_doc(
                    {
                        "doctype": "Role",
                        "role_name": role_data["role_name"],
                        "desk_access": role_data["desk_access"],
                        "description": role_data["description"],
                    }
                )
                role_doc.insert()
                frappe.logger().info(f"Rôle créé: {role_data['role_name']}")
            else:
                frappe.logger().info(f"Rôle existe déjà: {role_data['role_name']}")

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Erreur création rôles SMS: {e}")


def setup_default_permissions():
    """Configure les permissions par défaut"""
    try:
        # Permissions pour OVH SMS Settings
        setup_doctype_permissions(
            "OVH SMS Settings",
            [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1,
                },
                {"role": "SMS Manager", "read": 1, "write": 1},
                {"role": "SMS User", "read": 1},
            ],
        )

        # Permissions pour SMS Event Reminder
        setup_doctype_permissions(
            "SMS Event Reminder",
            [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1,
                },
                {"role": "SMS Manager", "read": 1, "write": 1},
                {"role": "SMS User", "read": 1},
            ],
        )

        frappe.logger().info("Permissions configurées avec succès")

    except Exception as e:
        frappe.log_error(f"Erreur configuration permissions: {e}")


def setup_doctype_permissions(doctype, permissions):
    """Configure les permissions pour un DocType"""
    try:
        for perm in permissions:
            # Vérifier si la permission existe déjà
            existing = frappe.db.exists(
                "DocPerm", {"parent": doctype, "role": perm["role"]}
            )

            if not existing:
                perm_doc = frappe.get_doc(
                    {
                        "doctype": "DocPerm",
                        "parent": doctype,
                        "parenttype": "DocType",
                        "parentfield": "permissions",
                        "role": perm["role"],
                        "read": perm.get("read", 0),
                        "write": perm.get("write", 0),
                        "create": perm.get("create", 0),
                        "delete": perm.get("delete", 0),
                        "submit": perm.get("submit", 0),
                        "cancel": perm.get("cancel", 0),
                        "amend": perm.get("amend", 0),
                    }
                )
                perm_doc.insert()

    except Exception as e:
        frappe.log_error(f"Erreur setup permissions {doctype}: {e}")


def setup_default_settings():
    """Configure les paramètres par défaut"""
    try:
        # Configuration par défaut pour SMS Event Reminder
        reminder_settings = frappe.get_single("SMS Event Reminder")
        if not reminder_settings.event_type_filter:
            reminder_settings.db_set("event_type_filter", "entretien")
            reminder_settings.db_set("reminder_hours_before", 24)
            reminder_settings.db_set("minimum_event_duration", 30)
            reminder_settings.db_set("business_hours_only", 0)
            reminder_settings.db_set("exclude_weekends", 0)
            reminder_settings.db_set("send_to_customer_only", 1)

            # Templates par défaut
            default_template = "Rappel : Vous avez un rendez-vous {{subject}} prévu le {{start_date}} à {{start_time}}. Merci de vous présenter à l'heure."
            reminder_settings.db_set("reminder_message_template", default_template)

            frappe.logger().info(
                "Paramètres par défaut configurés pour SMS Event Reminder"
            )

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Erreur configuration paramètres par défaut: {e}")


def setup_scheduler_events():
    """Configure les événements du scheduler"""
    try:
        # Vérifier que les tâches planifiées sont bien configurées
        scheduler_events = [
            "ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.process_event_reminders",
            "ovh_sms_integration.tasks.check_event_reminders_hourly",
            "ovh_sms_integration.tasks.reset_daily_counters",
            "ovh_sms_integration.tasks.cleanup_old_reminder_logs",
        ]

        for event in scheduler_events:
            try:
                # Test d'importation de la fonction
                module_path, function_name = event.rsplit(".", 1)
                module = frappe.get_module(module_path)
                if hasattr(module, function_name):
                    frappe.logger().info(f"Tâche planifiée validée: {event}")
                else:
                    frappe.logger().warning(f"Fonction introuvable: {event}")
            except Exception as e:
                frappe.logger().warning(f"Erreur validation tâche {event}: {e}")

    except Exception as e:
        frappe.log_error(f"Erreur configuration scheduler: {e}")


def show_installation_messages() -> None:
    """Affiche les messages de fin d'installation."""
    try:
        messages = [
            _("OVH SMS Integration installé avec succès !"),
            "",
            _("Étapes suivantes :"),
            _("1. Configurez vos paramètres OVH SMS dans : Setup > OVH SMS Settings"),
            _(
                "2. Configurez les rappels d'événements dans : Setup > SMS Event Reminder"
            ),
            _("3. Testez la connexion OVH depuis l'interface"),
            _("4. Créez vos expéditeurs SMS personnalisés"),
            _("5. Testez l'envoi de rappels avec un événement de test"),
            "",
            _("Rôles créés :"),
            _("- SMS Manager : Gestion complète des SMS"),
            _("- SMS User : Utilisation de base des SMS"),
            "",
            _("Tâches automatiques configurées :"),
            _("- Vérification des rappels (toutes les heures)"),
            _("- Reset des compteurs (quotidien)"),
            _("- Nettoyage des logs (hebdomadaire)"),
            "",
            _("Documentation disponible dans le README.md"),
        ]

        for msg in messages:
            if msg:
                frappe.logger().info(msg)

        # Affichage d'un message dans l'interface si possible
        if frappe.local.request:
            frappe.msgprint(
                "<br>".join(messages),
                title=_("Installation OVH SMS Integration"),
                indicator="green",
            )

    except Exception as e:
        frappe.log_error(f"Erreur affichage messages installation: {e}")


def before_uninstall():
    """Exécuté avant la désinstallation"""
    try:
        frappe.logger().info("Début désinstallation OVH SMS Integration")

        # Désactiver les rappels
        try:
            reminder_settings = frappe.get_single("SMS Event Reminder")
            reminder_settings.db_set("enabled", 0)
            frappe.logger().info("Rappels d'événements désactivés")
        except Exception:
            pass

        # Désactiver l'intégration OVH
        try:
            sms_settings = frappe.get_single("OVH SMS Settings")
            sms_settings.db_set("enabled", 0)
            frappe.logger().info("Intégration OVH SMS désactivée")
        except Exception:
            pass

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Erreur avant désinstallation: {e}")


def after_uninstall():
    """Exécuté après la désinstallation"""
    try:
        frappe.logger().info("Nettoyage post-désinstallation")

        # Optionnel : Supprimer les rôles créés
        # (Généralement on les garde pour éviter les problèmes)

        frappe.logger().info("Désinstallation OVH SMS Integration terminée")

    except Exception as e:
        frappe.log_error(f"Erreur après désinstallation: {e}")


def migrate_existing_data():
    """Migre les données existantes si nécessaire"""
    try:
        # Migration des anciens paramètres si l'app était déjà installée
        frappe.logger().info("Vérification migration données existantes")

        # Exemple de migration
        # if frappe.db.exists('OVH SMS Settings'):
        #     # Migrer les anciens paramètres
        #     pass

        frappe.logger().info("Migration données terminée")

    except Exception as e:
        frappe.log_error(f"Erreur migration données: {e}")


def validate_installation():
    """Valide que l'installation s'est bien déroulée"""
    try:
        validation_checks = []

        # Vérifier les DocTypes
        required_doctypes = ["OVH SMS Settings", "SMS Event Reminder"]
        for doctype in required_doctypes:
            if frappe.db.exists("DocType", doctype):
                validation_checks.append(f"✅ {doctype} créé")
            else:
                validation_checks.append(f"❌ {doctype} manquant")

        # Vérifier les rôles
        required_roles = ["SMS Manager", "SMS User"]
        for role in required_roles:
            if frappe.db.exists("Role", role):
                validation_checks.append(f"✅ Rôle {role} créé")
            else:
                validation_checks.append(f"❌ Rôle {role} manquant")

        # Vérifier les modules
        try:
            import ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder as _  # noqa: F401

            validation_checks.append("✅ Modules Python importables")
        except ImportError:
            validation_checks.append("❌ Erreur importation modules")

        # Log des résultats
        for check in validation_checks:
            frappe.logger().info(check)

        # Vérifier si tout est OK
        all_good = all("✅" in check for check in validation_checks)

        if all_good:
            frappe.logger().info("🎉 Installation validée avec succès !")
        else:
            frappe.logger().warning("⚠️ Problèmes détectés lors de la validation")

        return all_good

    except Exception as e:
        frappe.log_error(f"Erreur validation installation: {e}")
        return False
