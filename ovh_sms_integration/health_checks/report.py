# -*- coding: utf-8 -*-
"""Génération et affichage des rapports de santé."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def display_health_report(health_report: dict[str, Any]) -> None:
    """Affiche le rapport de santé final.

    Args:
        health_report: Rapport de santé complet à afficher.

    Note:
        Affiche:
        - Statut global (healthy/warning/error)
        - Résumé des vérifications
        - Détails des avertissements et erreurs
        - Recommandations
    """
    print("\n" + "=" * 60)
    print("📋 RAPPORT DE SANTÉ FINAL")
    print("=" * 60)

    # Statut global
    status_icon = {"healthy": "✅", "warning": "⚠️", "error": "❌"}

    status = health_report["overall_status"]
    print(f"\n🏥 Statut global: {status_icon[status]} {status.upper()}")

    # Résumé
    checks_count = len(health_report["checks"])
    warnings_count = len(health_report["warnings"])
    errors_count = len(health_report["errors"])

    print("\n📊 Résumé:")
    print(f"  ✅ Vérifications réussies: {checks_count}")
    print(f"  ⚠️ Avertissements: {warnings_count}")
    print(f"  ❌ Erreurs: {errors_count}")

    # Détails des avertissements
    if health_report["warnings"]:
        print("\n⚠️ Avertissements:")
        for warning in health_report["warnings"]:
            print(f"  - {warning}")

    # Détails des erreurs
    if health_report["errors"]:
        print("\n❌ Erreurs:")
        for error in health_report["errors"]:
            print(f"  - {error}")

    # Recommandations
    print("\n💡 Recommandations:")
    if errors_count > 0:
        print("  - Corrigez les erreurs avant de continuer")
        print("  - Vérifiez la configuration OVH SMS")
        print("  - Consultez les logs pour plus de détails")
    elif warnings_count > 0:
        print("  - Examinez les avertissements")
        print("  - Optimisez la configuration si nécessaire")
    else:
        print("  - Système en bonne santé !")
        print("  - Continuez à surveiller les statistiques")

    print(f"\n🕒 Vérification terminée: {health_report['timestamp']}")
    print("=" * 60)


def save_health_report(
    health_report: dict[str, Any], filename: str | None = None
) -> str | None:
    """Sauvegarde le rapport de santé dans un fichier JSON.

    Args:
        health_report: Rapport de santé à sauvegarder.
        filename: Nom du fichier (optionnel, généré automatiquement si non fourni).

    Returns:
        str | None: Chemin du fichier créé ou None en cas d'erreur.
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sms_health_report_{timestamp}.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(health_report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n💾 Rapport sauvegardé: {filename}")
        return filename
    except Exception as e:
        print(f"\n❌ Erreur sauvegarde rapport: {e}")
        return None
