frappe.ui.form.on("OVH SMS Settings", {
	refresh: function (frm) {
		// Ajouter des boutons personnalisés
		if (frm.doc.enabled) {
			frm.add_custom_button(__("Test Connection"), function () {
				test_ovh_connection(frm);
			});

			frm.add_custom_button(__("Check Balance"), function () {
				refresh_sms_balance(frm);
			});
		}
	},

	send_test_sms: function (frm) {
		if (!frm.doc.test_mobile) {
			frappe.msgprint(__("Please enter a test mobile number"));
			return;
		}

		frappe.call({
			method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.send_test_sms",
			callback: function (r) {
				if (r.message) {
					frm.reload_doc();
				}
			},
		});
	},

	refresh_balance: function (frm) {
		frappe.call({
			method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.refresh_balance",
			callback: function (r) {
				frm.reload_doc();
			},
		});
	},

	enabled: function (frm) {
		if (frm.doc.enabled) {
			frm.set_df_property("application_key", "reqd", 1);
			frm.set_df_property("application_secret", "reqd", 1);
			frm.set_df_property("consumer_key", "reqd", 1);
		} else {
			frm.set_df_property("application_key", "reqd", 0);
			frm.set_df_property("application_secret", "reqd", 0);
			frm.set_df_property("consumer_key", "reqd", 0);
		}
	},
});

function test_ovh_connection(frm) {
	frappe.call({
		method: "ovh_sms_integration.utils.sms_utils.test_ovh_connection",
		callback: function (r) {
			if (r.message) {
				if (r.message.success) {
					frappe.msgprint(__("Connection successful: ") + r.message.message);
				} else {
					frappe.msgprint(__("Connection failed: ") + r.message.message);
				}
			}
		},
	});
}

function refresh_sms_balance(frm) {
	frappe.call({
		method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.refresh_balance",
		callback: function (r) {
			frm.reload_doc();
		},
	});
}
