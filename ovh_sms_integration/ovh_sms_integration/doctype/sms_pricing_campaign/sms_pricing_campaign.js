// Script JavaScript pour SMS Pricing Campaign
// Fichier: ovh_sms_integration/ovh_sms_integration/doctype/sms_pricing_campaign/sms_pricing_campaign.js

frappe.ui.form.on("SMS Pricing Campaign", {
	refresh: function (frm) {
		// Boutons d'envoi SMS
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Send All SMS"),
				function () {
					send_all_campaign_sms(frm);
				},
				__("SMS Actions")
			);

			frm.add_custom_button(
				__("Send Selected SMS"),
				function () {
					send_selected_sms(frm);
				},
				__("SMS Actions")
			);

			frm.add_custom_button(
				__("Preview Messages"),
				function () {
					preview_campaign_messages(frm);
				},
				__("SMS Actions")
			);
		}

		// Bouton de test SMS
		frm.add_custom_button(
			__("Send Test SMS"),
			function () {
				send_test_sms(frm);
			},
			__("Test")
		);

		// Bouton de calcul des totaux
		frm.add_custom_button(
			__("Recalculate Totals"),
			function () {
				calculate_all_totals(frm);
			},
			__("Tools")
		);

		// Bouton pour remplir automatiquement les taux
		frm.add_custom_button(
			__("Auto-fill Rates"),
			function () {
				auto_fill_valuation_rates(frm);
			},
			__("Tools")
		);

		// Affichage du statut
		if (frm.doc.status) {
			const status_color = {
				"Brouillon": "grey",
				"Prêt": "blue",
				"Envoyé": "green",
				"Partiellement envoyé": "orange",
				"Annulé": "red"
			};

			frm.dashboard.add_comment(
				__(`Statut: ${frm.doc.status}`),
				status_color[frm.doc.status] || "grey",
				true
			);
		}

		// Indicateurs de performance
		if (frm.doc.sms_sent_count > 0) {
			frm.dashboard.add_comment(
				__(`${frm.doc.sms_sent_count} SMS envoyés - ${frm.doc.sms_failed_count} échecs`),
				frm.doc.sms_failed_count > 0 ? "orange" : "green",
				true
			);
		}

		// Avertissements
		if (frm.doc.enabled && !frm.doc.sms_template) {
			frm.dashboard.add_comment(
				__("Template SMS requis pour l'envoi"),
				"red",
				true
			);
		}
	},

	validate: function (frm) {
		// Validation avant sauvegarde
		if (frm.doc.pricing_items) {
			let has_errors = false;

			frm.doc.pricing_items.forEach((item, index) => {
				if (!item.customer_mobile) {
					frappe.msgprint({
						title: __("Mobile manquant"),
						message: __(`Numéro mobile requis pour ${item.customer_name || item.customer} (ligne ${index + 1})`),
						indicator: "red",
					});
					has_errors = true;
				}

				if (!item.base_rate || item.base_rate <= 0) {
					frappe.msgprint({
						title: __("Taux manquant"),
						message: __(`Taux de base requis pour ${item.item_name || item.item_code} (ligne ${index + 1})`),
						indicator: "red",
					});
					has_errors = true;
				}
			});

			if (has_errors) {
				frappe.validated = false;
			}
		}
	},

	pricing_items_add: function (frm, cdt, cdn) {
		// Événement ajout d'une ligne
		const row = locals[cdt][cdn];
		
		// Définir des valeurs par défaut
		row.qty = 1;
		row.margin_type = "Percentage";
		row.margin_percent = 20; // 20% de marge par défaut
		row.selected_for_sending = 1;
		row.currency = frm.doc.currency || "EUR";

		frm.refresh_field("pricing_items");
	},

	company: function (frm) {
		if (frm.doc.company) {
			// Mettre à jour la devise par défaut de la société
			frappe.db.get_value("Company", frm.doc.company, "default_currency")
				.then(r => {
					if (r.message && r.message.default_currency) {
						frm.set_value("currency", r.message.default_currency);
					}
				});
		}
	},

	sms_template: function (frm) {
		// Validation du template en temps réel
		if (frm.doc.sms_template) {
			validate_sms_template(frm.doc.sms_template);
		}
	}
});

// Événements pour les lignes de tarification
frappe.ui.form.on("SMS Pricing Item", {
	customer: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.customer) {
			// Récupérer automatiquement le mobile du client
			frappe.call({
				method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.get_customer_mobile",
				args: {
					customer: row.customer
				},
				callback: function (r) {
					if (r.message && r.message.success && r.message.mobile) {
						frappe.model.set_value(cdt, cdn, "customer_mobile", r.message.mobile);
						frappe.show_alert({
							message: __(`Mobile récupéré: ${r.message.mobile}`),
							indicator: "green"
						});
					} else {
						frappe.show_alert({
							message: __("Mobile non trouvé pour ce client"),
							indicator: "orange"
						});
					}
				}
			});
		}
	},

	item_code: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.item_code) {
			// Récupérer automatiquement le taux de valorisation
			frappe.call({
				method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.get_item_valuation_rate",
				args: {
					item_code: row.item_code
				},
				callback: function (r) {
					if (r.message && r.message.success && r.message.rate) {
						frappe.model.set_value(cdt, cdn, "base_rate", r.message.rate);
						calculate_item_total(frm, cdt, cdn);
						
						frappe.show_alert({
							message: __(`Taux récupéré: ${r.message.rate}€`),
							indicator: "green"
						});
					} else {
						frappe.show_alert({
							message: __("Taux de valorisation non trouvé"),
							indicator: "orange"
						});
					}
				}
			});
		}
	},

	qty: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	base_rate: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	margin_type: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		
		// Reset des valeurs de marge lors du changement de type
		if (row.margin_type === "Percentage") {
			frappe.model.set_value(cdt, cdn, "margin_amount", 0);
		} else {
			frappe.model.set_value(cdt, cdn, "margin_percent", 0);
		}
		
		calculate_item_total(frm, cdt, cdn);
	},

	margin_percent: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	margin_amount: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	customer_mobile: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		
		if (row.customer_mobile) {
			// Formatage automatique du numéro
			const formatted_mobile = format_phone_number(row.customer_mobile);
			if (formatted_mobile !== row.customer_mobile) {
				frappe.model.set_value(cdt, cdn, "customer_mobile", formatted_mobile);
			}
		}
	}
});

// Fonctions utilitaires

function calculate_item_total(frm, cdt, cdn) {
	"""Calcule le total pour une ligne"""
	const row = locals[cdt][cdn];
	
	if (!row.base_rate || !row.qty) {
		return;
	}

	const base_amount = row.base_rate * row.qty;
	let margin_value = 0;

	// Calcul de la marge
	if (row.margin_type === "Percentage") {
		margin_value = base_amount * (row.margin_percent || 0) / 100;
	} else {
		margin_value = (row.margin_amount || 0) * row.qty;
	}

	// Prix final
	const rate_with_margin = row.base_rate + (margin_value / row.qty);
	const amount = rate_with_margin * row.qty;

	frappe.model.set_value(cdt, cdn, "rate_with_margin", rate_with_margin);
	frappe.model.set_value(cdt, cdn, "amount", amount);

	// Recalcul des totaux de la campagne
	setTimeout(() => {
		calculate_campaign_totals(frm);
	}, 100);
}

function calculate_campaign_totals(frm) {
	"""Calcule les totaux de la campagne"""
	if (!frm.doc.pricing_items) {
		return;
	}

	let total_items = frm.doc.pricing_items.length;
	let unique_customers = new Set();
	let total_amount = 0;
	let total_margin = 0;
	const sms_cost = 0.10; // Coût par SMS

	frm.doc.pricing_items.forEach(item => {
		unique_customers.add(item.customer);
		total_amount += item.amount || 0;

		// Calcul de la marge
		const base_amount = (item.base_rate || 0) * (item.qty || 1);
		const margin_amount = (item.amount || 0) - base_amount;
		total_margin += margin_amount;
	});

	// Mise à jour des champs
	frm.set_value("total_items", total_items);
	frm.set_value("total_customers", unique_customers.size);
	frm.set_value("total_sms_cost", unique_customers.size * sms_cost);
	frm.set_value("estimated_revenue", total_amount);
	frm.set_value("profit_potential", total_margin);

	// Calcul marge moyenne
	if (total_amount > 0) {
		const average_margin = (total_margin / (total_amount - total_margin)) * 100;
		frm.set_value("average_margin_percent", average_margin);
	} else {
		frm.set_value("average_margin_percent", 0);
	}
}

function calculate_all_totals(frm) {
	"""Recalcule tous les totaux"""
	if (!frm.doc.pricing_items) {
		frappe.msgprint(__("Aucune ligne à calculer"));
		return;
	}

	// Recalcul de chaque ligne
	frm.doc.pricing_items.forEach((item, index) => {
		const cdt = item.doctype;
		const cdn = item.name;
		calculate_item_total(frm, cdt, cdn);
	});

	frappe.show_alert({
		message: __("Totaux recalculés"),
		indicator: "green"
	});
}

function auto_fill_valuation_rates(frm) {
	"""Remplit automatiquement les taux de valorisation"""
	if (!frm.doc.pricing_items) {
		frappe.msgprint(__("Aucune ligne trouvée"));
		return;
	}

	let promises = [];
	let updated_count = 0;

	frm.doc.pricing_items.forEach((item, index) => {
		if (item.item_code && !item.base_rate) {
			const promise = frappe.call({
				method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.get_item_valuation_rate",
				args: {
					item_code: item.item_code
				}
			}).then(r => {
				if (r.message && r.message.success && r.message.rate) {
					item.base_rate = r.message.rate;
					updated_count++;
				}
			});
			
			promises.push(promise);
		}
	});

	Promise.all(promises).then(() => {
		if (updated_count > 0) {
			frm.refresh_field("pricing_items");
			calculate_all_totals(frm);
			
			frappe.show_alert({
				message: __(`${updated_count} taux mis à jour`),
				indicator: "green"
			});
		} else {
			frappe.show_alert({
				message: __("Aucun taux à mettre à jour"),
				indicator: "blue"
			});
		}
	});
}

function send_all_campaign_sms(frm) {
	"""Envoie tous les SMS de la campagne"""
	frappe.confirm(
		__("Envoyer les SMS à tous les clients de la campagne ?"),
		function () {
			frappe.call({
				method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.send_all_campaign_sms",
				args: {
					campaign_name: frm.doc.name
				},
				callback: function (r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("SMS Envoyés"),
							message: r.message.message,
							indicator: "green"
						});
						
						frm.refresh();
					} else {
						frappe.msgprint({
							title: __("Erreur"),
							message: r.message.message || "Erreur lors de l'envoi",
							indicator: "red"
						});
					}
				}
			});
		}
	);
}

function send_selected_sms(frm) {
	"""Envoie les SMS sélectionnés"""
	const selected_count = frm.doc.pricing_items.filter(item => 
		item.selected_for_sending && !item.sms_sent
	).length;

	if (selected_count === 0) {
		frappe.msgprint(__("Aucun élément sélectionné pour l'envoi"));
		return;
	}

	frappe.confirm(
		__(`Envoyer les SMS aux ${selected_count} clients sélectionnés ?`),
		function () {
			frappe.call({
				method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.send_selected_sms",
				args: {
					campaign_name: frm.doc.name
				},
				callback: function (r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("SMS Envoyés"),
							message: r.message.message,
							indicator: "green"
						});
						
						frm.refresh();
					} else {
						frappe.msgprint({
							title: __("Erreur"),
							message: r.message.message || "Erreur lors de l'envoi",
							indicator: "red"
						});
					}
				}
			});
		}
	);
}

function preview_campaign_messages(frm) {
	"""Affiche un aperçu des messages SMS"""
	frappe.call({
		method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.preview_campaign_sms",
		args: {
			campaign_name: frm.doc.name
		},
		callback: function (r) {
			if (r.message && r.message.success) {
				const previews = r.message.previews;

				if (previews.length === 0) {
					frappe.msgprint(__("Aucun message à prévisualiser"));
					return;
				}

				let message_html = `<div style="font-size: 14px;">
					<h6>Aperçu des messages SMS (${previews.length} premiers):</h6>`;

				previews.forEach((preview, index) => {
					message_html += `
						<div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;">
							<p><strong>Client:</strong> ${preview.customer}</p>
							<p><strong>Mobile:</strong> ${preview.mobile}</p>
							<p><strong>Article:</strong> ${preview.item}</p>
							<p><strong>Prix:</strong> ${preview.price}€</p>
							<div style="background: #f8f9fa; padding: 10px; border-radius: 3px;">
								<strong>Message:</strong><br>
								${preview.message.replace(/\n/g, '<br>')}
							</div>
						</div>
					`;
				});

				message_html += `</div>`;

				frappe.msgprint({
					title: __("Aperçu Messages SMS"),
					message: message_html,
					indicator: "blue"
				});
			} else {
				frappe.msgprint({
					title: __("Erreur"),
					message: r.message.message || "Erreur lors de la génération",
					indicator: "red"
				});
			}
		}
	});
}

function send_test_sms(frm) {
	"""Envoie un SMS de test"""
	if (!frm.doc.test_mobile) {
		frappe.prompt(
			{
				fieldname: "test_mobile",
				label: __("Numéro de test"),
				fieldtype: "Data",
				reqd: 1,
				description: __("Format: +33123456789")
			},
			function (values) {
				execute_test_sms(frm, values.test_mobile);
			},
			__("SMS de Test"),
			__("Envoyer")
		);
	} else {
		execute_test_sms(frm, frm.doc.test_mobile);
	}
}

function execute_test_sms(frm, mobile) {
	"""Exécute l'envoi du SMS de test"""
	frappe.call({
		method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.send_test_campaign_sms",
		args: {
			campaign_name: frm.doc.name,
			test_mobile: mobile
		},
		callback: function (r) {
			if (r.message && r.message.success) {
				frappe.msgprint({
					title: __("SMS Test Envoyé"),
					message: `${r.message.message}<br><br><strong>Contenu:</strong><br>${r.message.content}`,
					indicator: "green"
				});
			} else {
				frappe.msgprint({
					title: __("Erreur SMS Test"),
					message: r.message.message || "Erreur lors de l'envoi",
					indicator: "red"
				});
			}
		}
	});
}

function validate_sms_template(template) {
	"""Valide le template SMS"""
	const required_vars = ["{{customer_name}}", "{{item_name}}", "{{final_price}}"];
	const missing_vars = [];

	required_vars.forEach(variable => {
		if (!template.includes(variable)) {
			missing_vars.push(variable);
		}
	});

	if (missing_vars.length > 0) {
		frappe.show_alert({
			message: __(`Variables recommandées manquantes: ${missing_vars.join(", ")}`),
			indicator: "orange"
		});
	}

	// Validation de la longueur
	if (template.length > 160) {
		frappe.show_alert({
			message: __(`Message long (${template.length} caractères). Coût SMS multiple.`),
			indicator: "orange"
		});
	}
}

function format_phone_number(phone) {
	"""Formate un numéro de téléphone"""
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