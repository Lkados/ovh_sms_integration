from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "module_name": "OVH SMS Integration",
            "color": "blue",
            "icon": "octicon octicon-device-mobile",
            "type": "module",
            "label": _("OVH SMS")
        }
    ]