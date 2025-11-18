"""
API module for OVH SMS Integration.

This module exports all API endpoints for SMS functionality.
"""

# Employee SMS API
from ovh_sms_integration.api.employee import (  # noqa: F401
    check_sms_quota,
    get_employee_mobile,
    get_employees_with_mobile,
    send_sms_to_employees,
)

__all__ = [
    # Employee SMS
    "check_sms_quota",
    "get_employee_mobile",
    "get_employees_with_mobile",
    "send_sms_to_employees",
]
