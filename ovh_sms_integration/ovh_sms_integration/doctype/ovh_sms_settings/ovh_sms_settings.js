// Script JavaScript pour OVH SMS Settings
// Fichier: ovh_sms_integration/ovh_sms_integration/doctype/ovh_sms_settings/ovh_sms_settings.js

frappe.ui.form.on("OVH SMS Settings", {
	refresh: function (frm) {
		// Bouton Test Connection
		frm.add_custom_button(
			__("Test Connection"),
			function () {
				frappe.call({
					method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.test_ovh_connection",
					callback: function (r) {
						if (r.message) {
							if (r.message.success) {
								frappe.msgprint({
									title: __("Connexion Réussie"),
									message: r.message.message,
									indicator: "green",
								});
							} else {
								frappe.msgprint({
									title: __("Erreur de Connexion"),
									message: r.message.message,
									indicator: "red",
								});
							}
						}
					},
				});
			},
			__("Actions")
		);

		// Bouton Send Test SMS
		frm.add_custom_button(
			__("Send Test SMS"),
			function () {
				// Dialog pour demander le numéro
				frappe.prompt(
					[
						{
							fieldname: "phone_number",
							label: __("Numéro de téléphone"),
							fieldtype: "Data",
							reqd: 1,
							description: __("Format: +33123456789 ou 0123456789"),
						},
						{
							fieldname: "message",
							label: __("Message"),
							fieldtype: "Small Text",
							default:
								"Test SMS depuis ERPNext - " + new Date().toLocaleTimeString(),
							reqd: 1,
						},
					],
					function (values) {
						// Envoi du SMS avec les valeurs saisies
						frappe.call({
							method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.send_test_sms",
							args: {
								phone_number: values.phone_number,
								message: values.message,
							},
							callback: function (r) {
								if (r.message) {
									if (r.message.success) {
										frappe.msgprint({
											title: __("SMS Envoyé"),
											message: r.message.message,
											indicator: "green",
										});
									} else {
										frappe.msgprint({
											title: __("Erreur Envoi SMS"),
											message: r.message.message,
											indicator: "red",
										});
									}
								}
							},
						});
					},
					__("Envoyer SMS de Test"),
					__("Envoyer")
				);
			},
			__("Actions")
		);

		// Bouton Account Balance
		frm.add_custom_button(
			__("Check Balance"),
			function () {
				frappe.call({
					method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.get_account_balance",
					callback: function (r) {
						if (r.message) {
							if (r.message.success) {
								frappe.msgprint({
									title: __("Solde Compte SMS"),
									message: `
                                    <div style="font-size: 14px;">
                                        <p><strong>Service:</strong> ${r.message.service_name}</p>
                                        <p><strong>Crédits restants:</strong> ${r.message.credits}</p>
                                        <p><strong>Status:</strong> ${r.message.status}</p>
                                    </div>
                                `,
									indicator: "blue",
								});
							} else {
								frappe.msgprint({
									title: __("Erreur"),
									message: r.message.message,
									indicator: "red",
								});
							}
						}
					},
				});
			},
			__("Actions")
		);

		// Affichage d'info si activé
		if (frm.doc.enabled) {
			frm.dashboard.add_comment(__("OVH SMS Integration is enabled"), "green", true);
		} else {
			frm.dashboard.add_comment(__("OVH SMS Integration is disabled"), "red", true);
		}
	},

	// Validation en temps réel
	application_key: function (frm) {
		if (frm.doc.application_key && frm.doc.application_key.length !== 16) {
			frappe.msgprint(__("Application Key doit faire 16 caractères"));
		}
	},

	application_secret: function (frm) {
		if (frm.doc.application_secret && frm.doc.application_secret.length !== 32) {
			frappe.msgprint(__("Application Secret doit faire 32 caractères"));
		}
	},

	consumer_key: function (frm) {
		if (frm.doc.consumer_key && frm.doc.consumer_key.length !== 32) {
			frappe.msgprint(__("Consumer Key doit faire 32 caractères"));
		}
	},
});
