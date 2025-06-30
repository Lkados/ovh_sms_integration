// Script JavaScript pour OVH SMS Settings - Version corrigée avec gestion des expéditeurs
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
									message: r.message.message.replace(/\n/g, "<br>"),
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

		// Bouton pour voir les expéditeurs disponibles
		frm.add_custom_button(
			__("View Senders"),
			function () {
				frappe.call({
					method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.get_available_senders",
					callback: function (r) {
						if (r.message && r.message.success) {
							const senders = r.message.senders;
							let message = `<div style="font-size: 14px;">
								<p><strong>Expéditeurs SMS disponibles:</strong></p>`;

							if (senders.length > 0) {
								message += `<ul>`;
								senders.forEach((sender) => {
									message += `<li>${sender}</li>`;
								});
								message += `</ul>`;
							} else {
								message += `<p style="color: orange;">Aucun expéditeur configuré</p>`;
							}

							message += `</div>`;

							frappe.msgprint({
								title: __("Expéditeurs SMS"),
								message: message,
								indicator: "blue",
							});
						} else {
							frappe.msgprint({
								title: __("Erreur"),
								message:
									r.message?.message ||
									"Erreur lors de la récupération des expéditeurs",
								indicator: "red",
							});
						}
					},
				});
			},
			__("Actions")
		);

		// Bouton pour créer un nouvel expéditeur
		frm.add_custom_button(
			__("Create Sender"),
			function () {
				frappe.prompt(
					[
						{
							fieldname: "sender_name",
							label: __("Nom de l'expéditeur"),
							fieldtype: "Data",
							reqd: 1,
							description: __("Nom alphanumérique uniquement, max 11 caractères"),
						},
						{
							fieldname: "description",
							label: __("Description"),
							fieldtype: "Data",
							default: "ERPNext Sender",
							reqd: 1,
						},
					],
					function (values) {
						frappe.call({
							method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.create_new_sender",
							args: {
								sender_name: values.sender_name,
								description: values.description,
							},
							callback: function (r) {
								if (r.message) {
									if (r.message.success) {
										frappe.msgprint({
											title: __("Expéditeur Créé"),
											message: r.message.message,
											indicator: "green",
										});
									} else {
										frappe.msgprint({
											title: __("Erreur Création Expéditeur"),
											message: r.message.message,
											indicator: "red",
										});
									}
								}
							},
						});
					},
					__("Créer Expéditeur SMS"),
					__("Créer")
				);
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
						// Validation du numéro de téléphone
						let phone = values.phone_number.replace(/[^\d+]/g, "");
						if (phone.startsWith("0")) {
							phone = "+33" + phone.substring(1);
						} else if (!phone.startsWith("+")) {
							phone = "+33" + phone;
						}

						// Envoi du SMS avec les valeurs saisies
						frappe.call({
							method: "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.send_test_sms",
							args: {
								phone_number: phone,
								message: values.message,
							},
							callback: function (r) {
								if (r.message) {
									if (r.message.success) {
										let msg = r.message.message;
										if (r.message.sender_used) {
											msg += `<br><small>Expéditeur utilisé: ${r.message.sender_used}</small>`;
										}

										frappe.msgprint({
											title: __("SMS Envoyé"),
											message: msg,
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

		// Afficher des conseils si l'expéditeur par défaut n'est pas configuré
		if (frm.doc.enabled && !frm.doc.default_sender) {
			frm.dashboard.add_comment(
				__("Conseil: Configurez un expéditeur par défaut pour éviter les erreurs"),
				"orange",
				true
			);
		}
	},

	// Validation en temps réel
	application_key: function (frm) {
		if (frm.doc.application_key && frm.doc.application_key.length !== 16) {
			frappe.msgprint({
				title: __("Attention"),
				message: __("Application Key doit généralement faire 16 caractères"),
				indicator: "orange",
			});
		}
	},

	application_secret: function (frm) {
		if (frm.doc.application_secret && frm.doc.application_secret.length !== 32) {
			frappe.msgprint({
				title: __("Attention"),
				message: __("Application Secret doit généralement faire 32 caractères"),
				indicator: "orange",
			});
		}
	},

	consumer_key: function (frm) {
		if (frm.doc.consumer_key && frm.doc.consumer_key.length !== 32) {
			frappe.msgprint({
				title: __("Attention"),
				message: __("Consumer Key doit généralement faire 32 caractères"),
				indicator: "orange",
			});
		}
	},

	default_sender: function (frm) {
		if (frm.doc.default_sender) {
			// Validation du format de l'expéditeur
			const sender = frm.doc.default_sender;
			const alphanumericRegex = /^[a-zA-Z0-9]+$/;

			if (!alphanumericRegex.test(sender)) {
				frappe.msgprint({
					title: __("Format invalide"),
					message: __(
						"L'expéditeur doit contenir uniquement des caractères alphanumériques"
					),
					indicator: "red",
				});
				return;
			}

			if (sender.length > 11) {
				frappe.msgprint({
					title: __("Trop long"),
					message: __("L'expéditeur ne peut pas dépasser 11 caractères"),
					indicator: "red",
				});
				return;
			}

			if (sender.length < 3) {
				frappe.msgprint({
					title: __("Trop court"),
					message: __("L'expéditeur doit faire au moins 3 caractères"),
					indicator: "orange",
				});
			}
		}
	},

	enabled: function (frm) {
		// Lorsque l'intégration est activée, afficher des conseils
		if (frm.doc.enabled) {
			frappe.show_alert({
				message: __(
					"N'oubliez pas de tester la connexion après avoir configuré les paramètres"
				),
				indicator: "blue",
			});
		}
	},

	auto_detect_service: function (frm) {
		// Basculer la visibilité du champ service_name
		frm.toggle_reqd("service_name", !frm.doc.auto_detect_service);
		frm.toggle_display("service_name", !frm.doc.auto_detect_service);
	},
});

// Fonction utilitaire pour formater les numéros de téléphone
function format_phone_number(phone) {
	if (!phone) return phone;

	// Supprimer tous les caractères non numériques sauf le +
	let cleaned = phone.replace(/[^\d+]/g, "");

	// Si commence par 0, remplacer par +33
	if (cleaned.startsWith("0")) {
		cleaned = "+33" + cleaned.substring(1);
	}
	// Si ne commence pas par +, ajouter +33
	else if (!cleaned.startsWith("+")) {
		cleaned = "+33" + cleaned;
	}

	return cleaned;
}

// Fonction pour valider un expéditeur SMS
function validate_sender_name(sender) {
	if (!sender) return false;

	// Vérifier le format alphanumérique
	const alphanumericRegex = /^[a-zA-Z0-9]+$/;
	if (!alphanumericRegex.test(sender)) {
		return {
			valid: false,
			message: "L'expéditeur doit contenir uniquement des caractères alphanumériques",
		};
	}

	// Vérifier la longueur
	if (sender.length > 11) {
		return {
			valid: false,
			message: "L'expéditeur ne peut pas dépasser 11 caractères",
		};
	}

	if (sender.length < 3) {
		return {
			valid: false,
			message: "L'expéditeur doit faire au moins 3 caractères",
		};
	}

	return {
		valid: true,
		message: "Format valide",
	};
}
