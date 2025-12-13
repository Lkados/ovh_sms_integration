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
            return {"status": "error", "message": _("ID employé requis")}

        # Récupérer l'employé
        employee = frappe.get_doc("Employee", employee_id)

        if not employee:
            return {
                "status": "error",
                "message": _("Employé {0} introuvable").format(employee_id),
            }

        # Essayer différents champs possibles (selon la version d'ERPNext)
        mobile = (
            getattr(employee, "cell_number", None)
            or getattr(employee, "mobile_no", None)
            or getattr(employee, "personal_mobile", None)
            or getattr(employee, "mobile", None)
            or getattr(employee, "phone", None)
        )

        if not mobile:
            return {
                "status": "error",
                "message": _("Aucun numéro de téléphone pour {0}").format(
                    employee.employee_name
                ),
                "employee_name": employee.employee_name,
            }

        return {
            "status": "success",
            "mobile": mobile,
            "employee_name": employee.employee_name,
        }

    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": _("Employé {0} introuvable").format(employee_id),
        }
    except Exception as e:
        frappe.log_error(
            f"Erreur get_employee_mobile: {str(e)}", "SMS Integration Error"
        )
        return {
            "status": "error",
            "message": _("Erreur lors de la récupération du mobile: {0}").format(
                str(e)
            ),
        }


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
        return {
            "status": "error",
            "message": "Module ovh_sms_integration non disponible",
        }
    except Exception as e:
        frappe.log_error(f"Erreur check_sms_quota: {str(e)}", "SMS Integration Error")
        return {
            "status": "error",
            "message": _("Erreur lors de la vérification du quota: {0}").format(str(e)),
        }


@frappe.whitelist()
def send_sms_to_employees(
    employee_ids: str | list[str], message: str, sender_name: str | None = None
) -> dict[str, Any]:
    """Envoie un SMS à un ou plusieurs employés.

    Args:
        employee_ids: ID(s) de(s) employé(s) destinataire(s).
        message: Contenu du SMS à envoyer.
        sender_name: Nom de l'expéditeur (optionnel).

    Returns:
        dict: Résultat avec status, total, sent, failed, results, message.

    Raises:
        frappe.PermissionError: Si l'utilisateur n'a pas la permission.
    """
    try:
        # 1. Parser et valider les entrées
        employee_ids_list = _parse_employee_ids(employee_ids)
        if not employee_ids_list:
            return {"status": "error", "message": _("Aucun employé sélectionné")}

        # 2. Vérifier quota
        quota_check = _check_quota_for_sending(len(employee_ids_list))
        if quota_check:
            return quota_check

        # 3. Valider et formater le message
        if not message or len(message.strip()) == 0:
            return {"status": "error", "message": _("Le message ne peut pas être vide")}

        formatted_message = _format_message_with_sender(message, sender_name)

        # 4. Envoyer à chaque employé
        results, sent_count, failed_count = _send_to_employee_list(
            employee_ids_list, formatted_message, sender_name
        )

        # 5. Retourner le résultat
        return _build_send_result(
            len(employee_ids_list), sent_count, failed_count, results
        )

    except frappe.PermissionError:
        raise
    except ImportError as e:
        frappe.log_error(
            f"Module SMS non disponible: {str(e)}", "SMS Integration Error"
        )
        return {
            "status": "error",
            "message": _("Module SMS non disponible. Contactez votre administrateur."),
        }
    except Exception as e:
        frappe.log_error(
            f"Erreur send_sms_to_employees: {str(e)}", "SMS Integration Error"
        )
        return {
            "status": "error",
            "message": _("Erreur lors de l'envoi des SMS: {0}").format(str(e)),
        }


def _parse_employee_ids(employee_ids: str | list[str]) -> list[str]:
    """Parse les IDs d'employés depuis différents formats.

    Args:
        employee_ids: IDs en JSON string, liste, ou ID unique.

    Returns:
        list[str]: Liste des IDs d'employés.
    """
    import json

    if isinstance(employee_ids, str):
        try:
            parsed_ids = json.loads(employee_ids)
            if isinstance(parsed_ids, list):
                return parsed_ids
            return [employee_ids]
        except json.JSONDecodeError:
            return [employee_ids]
    elif isinstance(employee_ids, list):
        return employee_ids
    return []


def _check_quota_for_sending(total_employees: int) -> dict[str, Any] | None:
    """Vérifie le quota SMS disponible.

    Args:
        total_employees: Nombre d'employés à contacter.

    Returns:
        dict | None: Erreur si quota insuffisant, None sinon.
    """
    from ovh_sms_integration.permissions import check_user_sms_quota

    try:
        remaining_quota = check_user_sms_quota(frappe.session.user)
    except Exception as e:
        frappe.throw(
            _("Vous n'avez pas la permission d'envoyer des SMS: {0}").format(str(e)),
            frappe.PermissionError,
        )

    if remaining_quota < total_employees:
        return {
            "status": "error",
            "message": _(
                "Quota insuffisant. Vous avez {0} SMS restant(s) "
                "mais tentez d'envoyer à {1} employé(s)."
            ).format(remaining_quota, total_employees),
        }
    return None


def _format_message_with_sender(message: str, sender_name: str | None) -> str:
    """Formate le message avec la signature de l'expéditeur.

    Args:
        message: Message original.
        sender_name: Nom de l'expéditeur.

    Returns:
        str: Message formaté avec signature.
    """
    if not sender_name:
        sender_name = frappe.get_value("User", frappe.session.user, "full_name")
    return f"{message}\n\n- {sender_name}"


def _send_to_employee_list(
    employee_ids_list: list[str], formatted_message: str, sender_name: str | None
) -> tuple[list[dict[str, Any]], int, int]:
    """Envoie le SMS à une liste d'employés.

    Args:
        employee_ids_list: Liste des IDs d'employés.
        formatted_message: Message formaté à envoyer.
        sender_name: Nom de l'expéditeur pour les logs.

    Returns:
        tuple: (results, sent_count, failed_count)
    """
    from ovh_sms_integration.utils.sms_utils import send_sms

    results: list[dict[str, Any]] = []
    sent_count = 0
    failed_count = 0

    for employee_id in employee_ids_list:
        result = _send_sms_to_single_employee(
            employee_id, formatted_message, sender_name, send_sms
        )
        results.append(result)
        if result["status"] == "success":
            sent_count += 1
        else:
            failed_count += 1

    return results, sent_count, failed_count


def _send_sms_to_single_employee(
    employee_id: str, message: str, sender_name: str | None, send_sms_func: Any
) -> dict[str, Any]:
    """Envoie un SMS à un seul employé.

    Args:
        employee_id: ID de l'employé.
        message: Message à envoyer.
        sender_name: Nom de l'expéditeur.
        send_sms_func: Fonction d'envoi SMS.

    Returns:
        dict: Résultat de l'envoi.
    """
    try:
        employee_info = get_employee_mobile(employee_id)

        if employee_info["status"] != "success":
            return {
                "employee_id": employee_id,
                "employee_name": employee_info.get("employee_name", "Inconnu"),
                "status": "error",
                "message": employee_info.get("message", "Mobile introuvable"),
            }

        mobile = employee_info["mobile"]
        employee_name = employee_info["employee_name"]

        sms_result = send_sms_func(message, mobile)

        if sms_result and sms_result.get("success"):
            frappe.logger().info(
                f"SMS envoyé à {employee_name} ({mobile}) par {sender_name}"
            )
            return {
                "employee_id": employee_id,
                "employee_name": employee_name,
                "mobile": mobile,
                "status": "success",
                "message_id": (
                    sms_result.get("details", {}).get("ids", [None])[0]
                    if sms_result.get("details")
                    else None
                ),
                "message": _("Envoyé"),
            }
        else:
            return {
                "employee_id": employee_id,
                "employee_name": employee_name,
                "mobile": mobile,
                "status": "error",
                "message": (
                    sms_result.get("message", _("Échec d'envoi"))
                    if sms_result
                    else _("Aucune réponse du service SMS")
                ),
            }

    except Exception as e:
        frappe.log_error(
            f"Erreur envoi SMS à {employee_id}: {str(e)}", "SMS Integration Error"
        )
        return {"employee_id": employee_id, "status": "error", "message": str(e)}


def _build_send_result(
    total: int, sent: int, failed: int, results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Construit le résultat final de l'envoi.

    Args:
        total: Nombre total d'employés.
        sent: Nombre de SMS envoyés.
        failed: Nombre d'échecs.
        results: Détails par employé.

    Returns:
        dict: Résultat formaté.
    """
    if sent == total:
        status = "success"
        message = _("✅ {0}/{1} SMS envoyé(s) avec succès").format(sent, total)
    elif sent > 0:
        status = "partial"
        message = _("⚠️ {0}/{1} SMS envoyé(s), {2} échec(s)").format(sent, total, failed)
    else:
        status = "error"
        message = _("❌ Tous les envois ont échoué (0/{0})").format(total)

    return {
        "status": status,
        "total": total,
        "sent": sent,
        "failed": failed,
        "results": results,
        "message": message,
    }


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
        # Récupérer tous les employés actifs avec TOUS les champs possibles pour mobile
        # Différentes versions d'ERPNext utilisent différents noms de champs
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "employee_name", "designation"],
            order_by="employee_name",
        )

        # Filtrer ceux qui ont un mobile et enrichir les données
        employees_with_mobile = []
        for emp_data in employees:
            # Récupérer le document complet pour accéder à tous les champs
            emp = frappe.get_doc("Employee", emp_data.name)

            # Essayer différents champs possibles (selon la version d'ERPNext)
            mobile = (
                getattr(emp, "cell_number", None)
                or getattr(emp, "mobile_no", None)
                or getattr(emp, "personal_mobile", None)
                or getattr(emp, "mobile", None)
                or getattr(emp, "phone", None)
            )

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
        frappe.log_error(
            f"Erreur get_employees_with_mobile: {str(e)}", "SMS Integration Error"
        )
        return {
            "status": "error",
            "message": _("Erreur lors de la récupération des employés: {0}").format(
                str(e)
            ),
        }
