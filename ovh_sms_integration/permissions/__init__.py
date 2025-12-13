# -*- coding: utf-8 -*-
"""Permissions package for OVH SMS Integration.

Ce package gère les permissions, quotas, et la sécurité pour les campagnes SMS.
"""
from __future__ import annotations

from ovh_sms_integration.permissions.query import (
    get_campaign_permission_query_conditions,
    has_campaign_permission,
    validate_sms_permissions,
    validate_sms_sending_permission,
)
from ovh_sms_integration.permissions.quota import (
    check_user_sms_quota,
    get_user_sms_quota,
)
from ovh_sms_integration.permissions.security import (
    check_concurrent_campaigns,
    create_sms_roles,
    request_campaign_approval,
    setup_campaign_security,
    setup_default_permissions,
    setup_security_limits,
    validate_campaign_limits,
)
from ovh_sms_integration.permissions.gdpr import (
    anonymize_campaign_data,
    enforce_gdpr_compliance,
    validate_phone_consent,
)
from ovh_sms_integration.permissions.decorators import (
    log_sms_action,
    rate_limit_sms,
    require_sms_permission,
)
from ovh_sms_integration.permissions.activity import (
    log_sms_activity,
    notify_approvers,
)

__all__ = [
    # Query
    "get_campaign_permission_query_conditions",
    "has_campaign_permission",
    "validate_sms_permissions",
    "validate_sms_sending_permission",
    # Quota
    "check_user_sms_quota",
    "get_user_sms_quota",
    # Security
    "setup_campaign_security",
    "create_sms_roles",
    "setup_default_permissions",
    "setup_security_limits",
    "validate_campaign_limits",
    "check_concurrent_campaigns",
    "request_campaign_approval",
    # GDPR
    "validate_phone_consent",
    "enforce_gdpr_compliance",
    "anonymize_campaign_data",
    # Decorators
    "require_sms_permission",
    "log_sms_action",
    "rate_limit_sms",
    # Activity
    "log_sms_activity",
    "notify_approvers",
]
