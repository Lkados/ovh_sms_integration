// Script JavaScript pour SMS Event Reminder
// Fichier: ovh_sms_integration/ovh_sms_integration/doctype/sms_event_reminder/sms_event_reminder.js

frappe.ui.form.on("SMS Event Reminder", {
	refresh: function (frm) {
		// Bouton pour tester les rappels
		frm.add_custom_button(
			__("Send Test Reminder"),
			function () {
				if (!frm.doc.test_event) {
					frappe.msgprint({
						title: __("Événement requis"),
						message: __("Veuillez sélectionner un événement de test"),
						indicator: "orange",
					});
					return;
				}

				if (!frm.doc.test_customer_mobile && !frm.doc.test_employee_mobile) {
					frappe.msgprint({
						title: __("Numéro requis"),
						message: __("Veuillez saisir au moins un numéro de test"),
						indicator: "orange",
					});
					return;
				}

				frappe.call({
					method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.send_test_reminder",
					callback: function (r) {
						if (r.message) {
							if (r.message.success) {
								frappe.msgprint({
									title: __("Test Réussi"),
									message: r.message.message,
									indicator: "green",
								});
								frm.refresh_field("last_test_result");
							} else {
								frappe.msgprint({
									title: __("Erreur Test"),
									message: r.message.message,
									indicator: "red",
								});
							}
						}
					},
				});
			},
			__("Test")
		);

		// Bouton pour vérifier les événements en attente
		frm.add_custom_button(
			__("Check Pending Events"),
			function () {
				frappe.call({
					method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.get_pending_events",
					callback: function (r) {
						if (r.message) {
							const events = r.message.events || [];
							let message = `<div style="font-size: 14px;">
								<p><strong>Événements nécessitant un rappel:</strong></p>`;

							if (events.length > 0) {
								message += `<ul>`;
								events.forEach((event) => {
									const date = new Date(event.starts_on).toLocaleString("fr-FR");
									message += `<li><strong>${event.subject}</strong> - ${date}</li>`;
								});
								message += `</ul>`;
								message += `<p><small>Total: ${events.length} événement(s)</small></p>`;
							} else {
								message += `<p style="color: #17a2b8;">Aucun événement en attente de rappel</p>`;
							}

							message += `</div>`;

							frappe.msgprint({
								title: __("Événements en Attente"),
								message: message,
								indicator: "blue",
							});
						}
					},
				});
			},
			__("Test")
		);

		// Bouton pour forcer l'envoi des rappels
		frm.add_custom_button(
			__("Send Reminders Now"),
			function () {
				frappe.confirm(
					__("Voulez-vous forcer l'envoi des rappels maintenant ?"),
					function () {
						frappe.call({
							method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.process_event_reminders",
							callback: function (r) {
								frappe.msgprint({
									title: __("Rappels Traités"),
									message: __(
										"Le traitement des rappels a été lancé. Vérifiez les logs pour les détails."
									),
									indicator: "green",
								});
								frm.refresh();
							},
						});
					}
				);
			},
			__("Actions")
		);

		// Bouton pour voir les statistiques
		frm.add_custom_button(
			__("View Statistics"),
			function () {
				frappe.call({
					method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.get_reminder_statistics",
					callback: function (r) {
						if (r.message) {
							const stats = r.message;
							let message = `<div style="font-size: 14px;">
								<h6>Statistiques des Rappels:</h6>
								<table class="table table-bordered" style="margin-top: 10px;">
									<tr><td><strong>Total envoyés</strong></td><td>${stats.total_sent}</td></tr>
									<tr><td><strong>Envoyés aujourd'hui</strong></td><td>${stats.sent_today}</td></tr>
									<tr><td><strong>Échecs</strong></td><td>${stats.failed_count}</td></tr>
									<tr><td><strong>Dernière vérification</strong></td><td>${
										stats.last_check
											? new Date(stats.last_check).toLocaleString("fr-FR")
											: "Jamais"
									}</td></tr>
									<tr><td><strong>Prochaine vérification</strong></td><td>${
										stats.next_check
											? new Date(stats.next_check).toLocaleString("fr-FR")
											: "Non planifiée"
									}</td></tr>
								</table>
							</div>`;

							frappe.msgprint({
								title: __("Statistiques"),
								message: message,
								indicator: "blue",
							});
						}
					},
				});
			},
			__("Actions")
		);

		// Affichage du statut
		if (frm.doc.enabled) {
			frm.dashboard.add_comment(__("Rappels d'événements activés"), "green", true);
		} else {
			frm.dashboard.add_comment(__("Rappels d'événements désactivés"), "red", true);
		}

		// Affichage des conseils
		if (frm.doc.enabled && !frm.doc.event_type_filter) {
			frm.dashboard.add_comment(
				__("Configurez le type d'événement à surveiller"),
				"orange",
				true
			);
		}
	},

	enabled: function (frm) {
		if (frm.doc.enabled) {
			frappe.show_alert({
				message: __(
					"N'oubliez pas de configurer les templates de messages et tester les rappels"
				),
				indicator: "blue",
			});
		}
	},

	enable_multiple_reminders: function (frm) {
		frm.toggle_reqd("reminder_times", frm.doc.enable_multiple_reminders);
		frm.toggle_display("reminder_times", frm.doc.enable_multiple_reminders);

		if (frm.doc.enable_multiple_reminders && !frm.doc.reminder_times) {
			frm.set_value("reminder_times", "24,2,0.5");
		}
	},

	business_hours_only: function (frm) {
		frm.toggle_display("business_start_time", frm.doc.business_hours_only);
		frm.toggle_display("business_end_time", frm.doc.business_hours_only);
	},

	reminder_times: function (frm) {
		if (frm.doc.reminder_times) {
			// Validation du format
			const times = frm.doc.reminder_times.split(",");
			let valid = true;
			const cleanTimes = [];

			times.forEach((time) => {
				const num = parseFloat(time.trim());
				if (isNaN(num) || num <= 0) {
					valid = false;
				} else {
					cleanTimes.push(num);
				}
			});

			if (!valid) {
				frappe.msgprint({
					title: __("Format invalide"),
					message: __(
						"Utilisez des nombres positifs séparés par des virgules (ex: 24,2,0.5)"
					),
					indicator: "red",
				});
				return;
			}

			// Tri des heures par ordre décroissant
			cleanTimes.sort((a, b) => b - a);
			frm.set_value("reminder_times", cleanTimes.join(","));

			// Affichage d'un aperçu
			const preview = cleanTimes
				.map((t) => {
					if (t >= 24) return `${Math.floor(t / 24)}j ${t % 24}h`;
					if (t >= 1) return `${t}h`;
					return `${Math.floor(t * 60)}min`;
				})
				.join(", ");

			frappe.show_alert({
				message: __(`Rappels programmés: ${preview} avant l'événement`),
				indicator: "blue",
			});
		}
	},

	event_type_filter: function (frm) {
		if (frm.doc.event_type_filter) {
			// Vérification du nombre d'événements correspondants
			frappe.call({
				method: "frappe.client.get_count",
				args: {
					doctype: "Event",
					filters: {
						subject: ["like", `%${frm.doc.event_type_filter}%`],
						docstatus: 1,
						starts_on: [">", frappe.datetime.now_datetime()],
					},
				},
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({
							message: __(
								`${r.message} événement(s) trouvé(s) avec "${frm.doc.event_type_filter}"`
							),
							indicator: "blue",
						});
					}
				},
			});
		}
	},

	test_event: function (frm) {
		if (frm.doc.test_event) {
			// Récupération des détails de l'événement
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Event",
					name: frm.doc.test_event,
				},
				callback: function (r) {
					if (r.message) {
						const event = r.message;
						const startDate = new Date(event.starts_on).toLocaleString("fr-FR");

						frappe.show_alert({
							message: __(`Événement sélectionné: ${event.subject} - ${startDate}`),
							indicator: "blue",
						});

						// Auto-remplissage du message de test si vide
						if (!frm.doc.test_customer_mobile || !frm.doc.test_employee_mobile) {
							frappe.show_alert({
								message: __("N'oubliez pas de saisir les numéros de test"),
								indicator: "orange",
							});
						}
					}
				},
			});
		}
	},

	send_test_reminder: function (frm) {
		// Cette fonction est déclenchée par le bouton dans le JSON
		// Le code est dans la fonction refresh() ci-dessus
	},

	// Validation en temps réel des numéros de téléphone
	test_customer_mobile: function (frm) {
		if (frm.doc.test_customer_mobile) {
			const mobile = format_phone_number(frm.doc.test_customer_mobile);
			if (mobile !== frm.doc.test_customer_mobile) {
				frm.set_value("test_customer_mobile", mobile);
			}
		}
	},

	test_employee_mobile: function (frm) {
		if (frm.doc.test_employee_mobile) {
			const mobile = format_phone_number(frm.doc.test_employee_mobile);
			if (mobile !== frm.doc.test_employee_mobile) {
				frm.set_value("test_employee_mobile", mobile);
			}
		}
	},

	minimum_event_duration: function (frm) {
		if (frm.doc.minimum_event_duration < 0) {
			frm.set_value("minimum_event_duration", 0);
		}
	},

	reminder_hours_before: function (frm) {
		if (frm.doc.reminder_hours_before <= 0) {
			frappe.msgprint({
				title: __("Valeur invalide"),
				message: __("Les heures avant l'événement doivent être positives"),
				indicator: "red",
			});
			frm.set_value("reminder_hours_before", 24);
		}
	},
});

// Fonctions utilitaires
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

// Auto-refresh des statistiques toutes les 5 minutes si la page est active
let statsRefreshInterval;

frappe.ui.form.on("SMS Event Reminder", {
	onload: function (frm) {
		// Démarrer l'auto-refresh des stats
		if (frm.doc.enabled) {
			statsRefreshInterval = setInterval(() => {
				if (document.visibilityState === "visible") {
					frm.refresh_field("total_reminders_sent");
					frm.refresh_field("reminders_sent_today");
					frm.refresh_field("last_reminder_sent");
					frm.refresh_field("failed_reminders_count");
				}
			}, 300000); // 5 minutes
		}
	},

	on_unload: function () {
		// Nettoyer l'intervalle
		if (statsRefreshInterval) {
			clearInterval(statsRefreshInterval);
		}
	},
});

// Validation personnalisée du formulaire
frappe.ui.form.on("SMS Event Reminder", {
	validate: function (frm) {
		// Validation des templates
		if (frm.doc.enabled) {
			const templates = [
				frm.doc.reminder_message_template,
				frm.doc.customer_template,
				frm.doc.employee_template,
				frm.doc.default_template,
			].filter(Boolean);

			// Vérification que au moins un template est défini
			if (templates.length === 0) {
				frappe.msgprint({
					title: __("Template requis"),
					message: __("Au moins un template de message doit être défini"),
					indicator: "red",
				});
				frappe.validated = false;
				return;
			}

			// Validation de la syntaxe des templates
			templates.forEach((template) => {
				if (template.includes("{{") && template.includes("}}")) {
					// Vérification basique de la syntaxe Jinja2
					const varPattern = /\{\{[\s]*([^}]+)[\s]*\}\}/g;
					let match;
					while ((match = varPattern.exec(template)) !== null) {
						const varName = match[1].trim();
						const validVars = [
							"subject",
							"description",
							"start_date",
							"start_time",
							"event_name",
							"customer_name",
							"employee_name",
							"duration",
							"location",
						];

						if (!validVars.includes(varName)) {
							frappe.show_alert({
								message: __(`Variable inconnue dans le template: {{${varName}}}`),
								indicator: "orange",
							});
						}
					}
				}
			});
		}
	},
});
