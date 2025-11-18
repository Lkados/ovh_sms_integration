"""
API pour l'envoi de SMS aux employés.

Ce module fait partie de ovh_sms_integration et fournit des API
pour envoyer des SMS aux employés ERPNext.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
    pass


@frappe.whitelist()
def get_employee_mobile(employee_id: str) -> dict[str, Any]:
    """
    Récupère le numéro de téléphone mobile d'un employé.

    Args:
        employee_id: ID de l'employé (Employee.name).

    Returns:
        dict: {
            "status": "success" | "error",
            "mobile": str | None,
            "employee_name": str,
            "message": str (si erreur)
        }

    Example:
        >>> get_employee_mobile("EMP-001")
        {"status": "success", "mobile": "+33612345678", "employee_name": "Jean Dupont"}
    """
    try:
        if not employee_id:
            return {"status": "error", "message": "ID employé requis"}

        # Récupérer l'employé
        employee = frappe.get_doc("Employee", employee_id)

        if not employee:
            return {"status": "error", "message": f"Employé {employee_id} introuvable"}

        # Vérifier le numéro de téléphone
        mobile = employee.cell_number

        if not mobile:
            return {
                "status": "error",
                "message": f"Aucun numéro de téléphone pour {employee.employee_name}",
                "employee_name": employee.employee_name,
            }

        return {"status": "success", "mobile": mobile, "employee_name": employee.employee_name}

    except frappe.DoesNotExistError:
        return {"status": "error", "message": f"Employé {employee_id} introuvable"}
    except Exception as e:
        frappe.log_error(f"Erreur get_employee_mobile: {str(e)}", "SMS Integration Error")
        return {"status": "error", "message": f"Erreur lors de la récupération du mobile: {str(e)}"}


@frappe.whitelist()
def check_sms_quota() -> dict[str, Any]:
    """
    Vérifie le quota SMS disponible pour l'utilisateur actuel.

    Returns:
        dict: {
            "status": "success" | "error",
            "has_permission": bool,
            "remaining": int,
            "total": int,
            "message": str (si erreur)
        }

    Note:
        Utilise la fonction de ovh_sms_integration pour vérifier les quotas.
    """
    try:
        # Importer depuis l'app ovh_sms_integration
        from ovh_sms_integration.permissions import check_user_sms_quota

        # check_user_sms_quota retourne un int (nombre de SMS restants)
        remaining = check_user_sms_quota(frappe.session.user)

        # Déterminer le quota total en fonction du rôle
        user_roles = frappe.get_roles(frappe.session.user)
        if "System Manager" in user_roles:
            total = 9999
        elif "SMS Manager" in user_roles:
            total = 500
        elif "SMS User" in user_roles:
            total = 100
        else:
            total = 0

        return {
            "status": "success",
            "has_permission": total > 0,
            "remaining": remaining,
            "total": total,
        }

    except ImportError:
        return {"status": "error", "message": "Module ovh_sms_integration non disponible"}
    except Exception as e:
        frappe.log_error(f"Erreur check_sms_quota: {str(e)}", "SMS Integration Error")
        return {"status": "error", "message": f"Erreur lors de la vérification du quota: {str(e)}"}


@frappe.whitelist()
def send_sms_to_employees(
    employee_ids: str | list[str], message: str, sender_name: str | None = None
) -> dict[str, Any]:
    """
    Envoie un SMS à un ou plusieurs employés.

    Args:
        employee_ids: ID(s) de(s) employé(s) destinataire(s). Peut être:
            - Une chaîne JSON: '["EMP-001", "EMP-002"]'
            - Une liste Python: ["EMP-001", "EMP-002"]
            - Un seul ID: "EMP-001"
        message: Contenu du SMS à envoyer.
        sender_name: Nom de l'expéditeur (optionnel, utilise l'utilisateur actuel par défaut).

    Returns:
        dict: {
            "status": "success" | "partial" | "error",
            "total": int - Nombre total d'employés ciblés,
            "sent": int - Nombre de SMS envoyés avec succès,
            "failed": int - Nombre d'échecs,
            "results": list[dict] - Détails pour chaque employé,
            "message": str - Message récapitulatif
        }

    Raises:
        frappe.PermissionError: Si l'utilisateur n'a pas la permission d'envoyer des SMS.

    Example:
        >>> send_sms_to_employees(
        ...     ["EMP-001", "EMP-002"],
        ...     "Rappel: RDV client demain 9h",
        ...     "Manager"
        ... )
        {
            "status": "success",
            "total": 2,
            "sent": 2,
            "failed": 0,
            "results": [
                {"employee_id": "EMP-001", "employee_name": "Jean Dupont", "status": "success"},
                {"employee_id": "EMP-002", "employee_name": "Marie Martin", "status": "success"}
            ],
            "message": "2/2 SMS envoyés avec succès"
        }

    Note:
        - Vérifie les permissions SMS avant envoi
        - Vérifie que le quota est suffisant pour tous les SMS
        - Log chaque envoi dans SMS Log
        - Décrémente automatiquement le quota
        - Continue l'envoi même si certains échouent
    """
    try:
        # 1. Parser les IDs d'employés
        import json

        if isinstance(employee_ids, str):
            try:
                # Essayer de parser comme JSON
                parsed_ids = json.loads(employee_ids)
                if isinstance(parsed_ids, list):
                    employee_ids_list = parsed_ids
                else:
                    # Sinon c'est un seul ID
                    employee_ids_list = [employee_ids]
            except json.JSONDecodeError:
                # Pas du JSON, c'est un seul ID
                employee_ids_list = [employee_ids]
        elif isinstance(employee_ids, list):
            employee_ids_list = employee_ids
        else:
            return {"status": "error", "message": "Format d'IDs employés invalide"}

        if not employee_ids_list:
            return {"status": "error", "message": "Aucun employé sélectionné"}

        # 2. Vérifier les permissions et le quota
        from ovh_sms_integration.permissions import check_user_sms_quota

        # check_user_sms_quota retourne un int (nombre de SMS restants) ou lève une exception
        try:
            remaining_quota = check_user_sms_quota(frappe.session.user)
        except Exception as e:
            frappe.throw(
                _("Vous n'avez pas la permission d'envoyer des SMS: {0}").format(str(e)),
                frappe.PermissionError
            )

        # 3. Vérifier que le quota est suffisant pour tous les envois
        total_employees = len(employee_ids_list)

        if remaining_quota < total_employees:
            return {
                "status": "error",
                "message": (
                    f"Quota insuffisant. Vous avez {remaining_quota} SMS "
                    f"restant(s) mais tentez d'envoyer à {total_employees} "
                    f"employé(s)."
                ),
            }

        # 4. Valider le message
        if not message or len(message.strip()) == 0:
            return {"status": "error", "message": "Le message ne peut pas être vide"}

        # 5. Préparer le message avec signature
        if not sender_name:
            sender_name = frappe.get_value("User", frappe.session.user, "full_name")

        formatted_message = f"{message}\n\n- {sender_name}"

        # 6. Importer la fonction d'envoi SMS
        from ovh_sms_integration.utils.sms_utils import send_sms

        # 7. Envoyer à chaque employé
        results = []
        sent_count = 0
        failed_count = 0

        for employee_id in employee_ids_list:
            try:
                # Récupérer le mobile de l'employé
                employee_info = get_employee_mobile(employee_id)

                if employee_info["status"] != "success":
                    results.append(
                        {
                            "employee_id": employee_id,
                            "employee_name": employee_info.get("employee_name", "Inconnu"),
                            "status": "error",
                            "message": employee_info.get("message", "Mobile introuvable"),
                        }
                    )
                    failed_count += 1
                    continue

                mobile = employee_info["mobile"]
                employee_name = employee_info["employee_name"]

                # Envoyer le SMS
                sms_result = send_sms(formatted_message, mobile)

                if sms_result.get("status") == "success":
                    # Succès
                    results.append(
                        {
                            "employee_id": employee_id,
                            "employee_name": employee_name,
                            "mobile": mobile,
                            "status": "success",
                            "message_id": sms_result.get("message_id"),
                            "message": "Envoyé",
                        }
                    )
                    sent_count += 1

                    # Log pour traçabilité
                    frappe.log_error(
                        f"SMS envoyé à {employee_name} ({mobile}) par {sender_name}",
                        "SMS Calendar Success",
                    )
                else:
                    # Échec d'envoi
                    results.append(
                        {
                            "employee_id": employee_id,
                            "employee_name": employee_name,
                            "mobile": mobile,
                            "status": "error",
                            "message": sms_result.get("message", "Échec d'envoi"),
                        }
                    )
                    failed_count += 1

            except Exception as e:
                # Erreur pour cet employé spécifique
                results.append({"employee_id": employee_id, "status": "error", "message": str(e)})
                failed_count += 1
                frappe.log_error(
                    f"Erreur envoi SMS à {employee_id}: {str(e)}", "SMS Integration Error"
                )

        # 8. Déterminer le statut global
        if sent_count == total_employees:
            overall_status = "success"
            summary_message = f"✅ {sent_count}/{total_employees} SMS envoyé(s) avec succès"
        elif sent_count > 0:
            overall_status = "partial"
            summary_message = (
                f"⚠️ {sent_count}/{total_employees} SMS envoyé(s), {failed_count} échec(s)"
            )
        else:
            overall_status = "error"
            summary_message = f"❌ Tous les envois ont échoué (0/{total_employees})"

        return {
            "status": overall_status,
            "total": total_employees,
            "sent": sent_count,
            "failed": failed_count,
            "results": results,
            "message": summary_message,
        }

    except frappe.PermissionError:
        raise
    except ImportError as e:
        frappe.log_error(f"Module SMS non disponible: {str(e)}", "SMS Integration Error")
        return {
            "status": "error",
            "message": "Module SMS non disponible. Contactez votre administrateur.",
        }
    except Exception as e:
        frappe.log_error(f"Erreur send_sms_to_employees: {str(e)}", "SMS Integration Error")
        return {"status": "error", "message": f"Erreur lors de l'envoi des SMS: {str(e)}"}


@frappe.whitelist()
def get_employees_with_mobile() -> dict[str, Any]:
    """
    Récupère la liste des employés actifs avec leur numéro de mobile.

    Returns:
        dict: {
            "status": "success" | "error",
            "employees": list[dict] avec name, employee_name, mobile,
            "total": int
        }

    Note:
        Filtre uniquement les employés qui ont un numéro de téléphone configuré.
    """
    try:
        # Récupérer tous les employés actifs
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "employee_name", "cell_number", "designation"],
            order_by="employee_name",
        )

        # Filtrer ceux qui ont un mobile et enrichir les données
        employees_with_mobile = []
        for emp in employees:
            mobile = emp.cell_number
            if mobile:
                employees_with_mobile.append(
                    {
                        "name": emp.name,
                        "employee_name": emp.employee_name,
                        "mobile": mobile,
                        "designation": emp.designation or "",
                    }
                )

        return {
            "status": "success",
            "employees": employees_with_mobile,
            "total": len(employees_with_mobile),
        }

    except Exception as e:
        frappe.log_error(f"Erreur get_employees_with_mobile: {str(e)}", "SMS Integration Error")
        return {
            "status": "error",
            "message": f"Erreur lors de la récupération des employés: {str(e)}",
        }
