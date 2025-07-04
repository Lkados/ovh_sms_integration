frappe.ui.form.on("SMS Pricing Campaign", {
	refresh: function (frm) {
		// Boutons d'action personnalisés
		if (frm.doc.docstatus === 0) {
			// Mode brouillon
			frm.add_custom_button(
				__("Ajouter Article Rapide"),
				function () {
					add_quick_item(frm);
				},
				__("Outils")
			);

			frm.add_custom_button(
				__("Importer Articles"),
				function () {
					import_items_dialog(frm);
				},
				__("Outils")
			);

			frm.add_custom_button(
				__("Calculer Totaux"),
				function () {
					calculate_all_totals(frm);
				},
				__("Outils")
			);
		}

		if (frm.doc.docstatus === 1) {
			// Mode soumis
			frm.add_custom_button(
				__("Envoyer Tous SMS"),
				function () {
					send_all_sms(frm);
				},
				__("Actions SMS")
			);

			frm.add_custom_button(
				__("Envoyer Sélectionnés"),
				function () {
					send_selected_sms(frm);
				},
				__("Actions SMS")
			);

			frm.add_custom_button(
				__("Aperçu Messages"),
				function () {
					preview_messages(frm);
				},
				__("Actions SMS")
			);
		}

		// Bouton test toujours disponible
		frm.add_custom_button(
			__("Test SMS"),
			function () {
				test_sms_dialog(frm);
			},
			__("Test")
		);

		// Mise à jour de l'affichage
		update_dashboard(frm);
		refresh_totals(frm);
	},

	onload: function (frm) {
		// Configuration initiale
		if (frm.is_new()) {
			// Valeurs par défaut pour nouvelle campagne
			frm.set_value("currency", "EUR");
			frm.set_value("enabled", 1);
		}

		// Configuration des filtres
		setup_filters(frm);
	},

	validate: function (frm) {
		// Validation avant sauvegarde
		if (!frm.doc.pricing_items || frm.doc.pricing_items.length === 0) {
			frappe.msgprint(__("Veuillez ajouter au moins un article"));
			frappe.validated = false;
			return;
		}

		// Validation des lignes
		let has_errors = false;
		frm.doc.pricing_items.forEach((item, index) => {
			if (!item.customer_mobile) {
				frappe.msgprint(
					__(`Numéro mobile requis pour ${item.customer || "ligne " + (index + 1)}`)
				);
				has_errors = true;
			}
			if (!item.base_rate || item.base_rate <= 0) {
				frappe.msgprint(
					__(`Prix de base requis pour ${item.item_name || "ligne " + (index + 1)}`)
				);
				has_errors = true;
			}
		});

		if (has_errors) {
			frappe.validated = false;
		}
	},

	company: function (frm) {
		if (frm.doc.company) {
			// Mise à jour de la devise par défaut
			frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
				if (r.message && r.message.default_currency) {
					frm.set_value("currency", r.message.default_currency);
				}
			});
		}
	},

	sms_template: function (frm) {
		if (frm.doc.sms_template) {
			validate_sms_template(frm.doc.sms_template);
		}
	},
});

// Événements pour les lignes de tarification
frappe.ui.form.on("SMS Pricing Item", {
	pricing_items_add: function (frm, cdt, cdn) {
		// Valeurs par défaut pour nouvelle ligne
		const row = locals[cdt][cdn];
		row.qty = 1;
		row.margin_percent = 20;
		row.selected_for_sending = 1;
		row.currency = frm.doc.currency || "EUR";
		row.sms_status = "En attente";
		frm.refresh_field("pricing_items");
	},

	customer: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.customer) {
			// Récupération automatique du mobile et nom
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Customer",
					name: row.customer,
				},
				callback: function (r) {
					if (r.message) {
						const customer = r.message;

						// Nom du client
						frappe.model.set_value(cdt, cdn, "customer_name", customer.customer_name);

						// Numéro mobile
						let mobile = customer.mobile_no || customer.phone;
						if (mobile) {
							mobile = format_phone_number(mobile);
							frappe.model.set_value(cdt, cdn, "customer_mobile", mobile);
							frappe.show_alert({
								message: __(`Mobile récupéré: ${mobile}`),
								indicator: "green",
							});
						} else {
							frappe.show_alert({
								message: __("Aucun mobile trouvé pour ce client"),
								indicator: "orange",
							});
						}
					}
				},
			});
		}
	},

	item_code: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item_code) {
			// Récupération automatique des détails de l'article
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Item",
					name: row.item_code,
				},
				callback: function (r) {
					if (r.message) {
						const item = r.message;

						// Nom et UOM
						frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
						frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);

						// Prix de base (valorisation ou prix standard)
						if (item.standard_rate && item.standard_rate > 0) {
							frappe.model.set_value(cdt, cdn, "base_rate", item.standard_rate);
							calculate_item_total(frm, cdt, cdn);
						} else {
							// Essayer de récupérer le dernier prix de valorisation
							get_item_valuation_rate(row.item_code).then((rate) => {
								if (rate > 0) {
									frappe.model.set_value(cdt, cdn, "base_rate", rate);
									calculate_item_total(frm, cdt, cdn);
								}
							});
						}
					}
				},
			});
		}
	},

	qty: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	base_rate: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	margin_percent: function (frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
	},

	customer_mobile: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.customer_mobile) {
			const formatted = format_phone_number(row.customer_mobile);
			if (formatted !== row.customer_mobile) {
				frappe.model.set_value(cdt, cdn, "customer_mobile", formatted);
			}
		}
	},
});

// Fonctions utilitaires

function calculate_item_total(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (!row.base_rate || !row.qty) {
		return;
	}

	const base_amount = row.base_rate * row.qty;
	const margin_amount = (base_amount * (row.margin_percent || 0)) / 100;
	const final_price = row.base_rate + margin_amount / row.qty;
	const total_amount = final_price * row.qty;

	frappe.model.set_value(cdt, cdn, "final_price", final_price);
	frappe.model.set_value(cdt, cdn, "amount", total_amount);

	// Recalcul des totaux
	setTimeout(() => {
		calculate_campaign_totals(frm);
	}, 100);
}

function calculate_campaign_totals(frm) {
	if (!frm.doc.pricing_items) {
		return;
	}

	let total_items = frm.doc.pricing_items.length;
	let unique_customers = new Set();
	let total_amount = 0;
	let total_margin = 0;

	frm.doc.pricing_items.forEach((item) => {
		if (item.customer) {
			unique_customers.add(item.customer);
		}
		total_amount += item.amount || 0;

		const base_amount = (item.base_rate || 0) * (item.qty || 1);
		const margin_amount = (item.amount || 0) - base_amount;
		total_margin += margin_amount;
	});

	// Mise à jour des champs
	frm.set_value("total_items", total_items);
	frm.set_value("total_customers", unique_customers.size);
	frm.set_value("estimated_revenue", total_amount);
	frm.set_value("profit_potential", total_margin);
	frm.set_value("total_sms_cost", unique_customers.size * 0.1); // 0.10€ par SMS

	// Calcul marge moyenne
	if (total_amount > 0) {
		const avg_margin = (total_margin / (total_amount - total_margin)) * 100;
		frm.set_value("average_margin_percent", avg_margin);
	}
}

function calculate_all_totals(frm) {
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
		indicator: "green",
	});
}

function add_quick_item(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Ajouter Article Rapide"),
		fields: [
			{
				fieldname: "customer",
				label: __("Client"),
				fieldtype: "Link",
				options: "Customer",
				reqd: 1,
			},
			{
				fieldname: "item_code",
				label: __("Article"),
				fieldtype: "Link",
				options: "Item",
				reqd: 1,
			},
			{
				fieldname: "qty",
				label: __("Quantité"),
				fieldtype: "Float",
				default: 1,
				reqd: 1,
			},
			{
				fieldname: "base_rate",
				label: __("Prix de base"),
				fieldtype: "Currency",
				reqd: 1,
			},
			{
				fieldname: "margin_percent",
				label: __("Marge (%)"),
				fieldtype: "Percent",
				default: 20,
			},
		],
		primary_action: function () {
			const values = dialog.get_values();
			if (values) {
				// Ajouter la ligne
				const row = frm.add_child("pricing_items");
				row.customer = values.customer;
				row.item_code = values.item_code;
				row.qty = values.qty;
				row.base_rate = values.base_rate;
				row.margin_percent = values.margin_percent;
				row.selected_for_sending = 1;
				row.currency = frm.doc.currency;

				// Calculer et rafraîchir
				calculate_item_total(frm, row.doctype, row.name);
				frm.refresh_field("pricing_items");

				dialog.hide();
				frappe.show_alert({
					message: __("Article ajouté"),
					indicator: "green",
				});
			}
		},
		primary_action_label: __("Ajouter"),
	});

	dialog.show();
}

function import_items_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Importer Articles en Masse"),
		fields: [
			{
				fieldname: "customer",
				label: __("Client par défaut"),
				fieldtype: "Link",
				options: "Customer",
				reqd: 1,
			},
			{
				fieldname: "margin_percent",
				label: __("Marge par défaut (%)"),
				fieldtype: "Percent",
				default: 20,
			},
			{
				fieldname: "items_data",
				label: __("Articles (un par ligne: code_article,quantité,prix_base)"),
				fieldtype: "Text",
				reqd: 1,
				description: __("Format: ITEM001,1,100<br>ITEM002,2,50"),
			},
		],
		primary_action: function () {
			const values = dialog.get_values();
			if (values) {
				import_items_from_text(frm, values);
				dialog.hide();
			}
		},
		primary_action_label: __("Importer"),
	});

	dialog.show();
}

function import_items_from_text(frm, values) {
	const lines = values.items_data.split("\n");
	let added_count = 0;

	lines.forEach((line) => {
		line = line.trim();
		if (line) {
			const parts = line.split(",");
			if (parts.length >= 3) {
				const row = frm.add_child("pricing_items");
				row.customer = values.customer;
				row.item_code = parts[0].trim();
				row.qty = parseFloat(parts[1].trim()) || 1;
				row.base_rate = parseFloat(parts[2].trim()) || 0;
				row.margin_percent = values.margin_percent;
				row.selected_for_sending = 1;
				row.currency = frm.doc.currency;
				added_count++;
			}
		}
	});

	if (added_count > 0) {
		frm.refresh_field("pricing_items");
		calculate_campaign_totals(frm);
		frappe.show_alert({
			message: __(`${added_count} articles importés`),
			indicator: "green",
		});
	}
}

function test_sms_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Test SMS"),
		fields: [
			{
				fieldname: "test_mobile",
				label: __("Numéro de test"),
				fieldtype: "Data",
				reqd: 1,
				default: frm.doc.test_mobile,
			},
			{
				fieldname: "preview_message",
				label: __("Aperçu du message"),
				fieldtype: "Text",
				read_only: 1,
			},
		],
		primary_action: function () {
			const values = dialog.get_values();
			if (values) {
				send_test_sms(frm, values.test_mobile);
				dialog.hide();
			}
		},
		primary_action_label: __("Envoyer"),
	});

	// Générer un aperçu du message
	if (frm.doc.pricing_items && frm.doc.pricing_items.length > 0) {
		const sample_item = frm.doc.pricing_items[0];
		const preview = generate_sms_preview(frm.doc.sms_template, sample_item);
		dialog.set_value("preview_message", preview);
	}

	dialog.show();
}

function send_test_sms(frm, mobile) {
	if (!frm.doc.pricing_items || frm.doc.pricing_items.length === 0) {
		frappe.msgprint(__("Aucun article disponible pour le test"));
		return;
	}

	frappe.call({
		method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.send_test_sms",
		args: {
			campaign_name: frm.doc.name,
			test_mobile: mobile,
		},
		callback: function (r) {
			if (r.message && r.message.success) {
				frm.set_value("last_action_result", r.message.message);
				frappe.msgprint({
					title: __("SMS Test Envoyé"),
					message: r.message.message,
					indicator: "green",
				});
			} else {
				frappe.msgprint({
					title: __("Erreur"),
					message: r.message.message || "Erreur lors de l'envoi",
					indicator: "red",
				});
			}
		},
	});
}

function send_all_sms(frm) {
	if (!frm.doc.pricing_items || frm.doc.pricing_items.length === 0) {
		frappe.msgprint(__("Aucun article à envoyer"));
		return;
	}

	frappe.confirm(__(`Envoyer des SMS à ${frm.doc.total_customers} clients ?`), function () {
		frappe.call({
			method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.send_all_sms",
			args: {
				campaign_name: frm.doc.name,
			},
			callback: function (r) {
				handle_sms_response(frm, r);
			},
		});
	});
}

function send_selected_sms(frm) {
	const selected = frm.doc.pricing_items.filter(
		(item) => item.selected_for_sending && !item.sms_sent
	);

	if (selected.length === 0) {
		frappe.msgprint(__("Aucun élément sélectionné"));
		return;
	}

	frappe.confirm(
		__(`Envoyer des SMS aux ${selected.length} éléments sélectionnés ?`),
		function () {
			frappe.call({
				method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.send_selected_sms",
				args: {
					campaign_name: frm.doc.name,
				},
				callback: function (r) {
					handle_sms_response(frm, r);
				},
			});
		}
	);
}

function handle_sms_response(frm, r) {
	if (r.message && r.message.success) {
		frm.set_value("last_action_result", r.message.message);
		frm.refresh();
		frappe.msgprint({
			title: __("SMS Envoyés"),
			message: r.message.message,
			indicator: "green",
		});
	} else {
		frappe.msgprint({
			title: __("Erreur"),
			message: r.message.message || "Erreur lors de l'envoi",
			indicator: "red",
		});
	}
}

function preview_messages(frm) {
	frappe.call({
		method: "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.preview_messages",
		args: {
			campaign_name: frm.doc.name,
		},
		callback: function (r) {
			if (r.message && r.message.success) {
				show_preview_dialog(r.message.previews);
			} else {
				frappe.msgprint({
					title: __("Erreur"),
					message: r.message.message || "Erreur génération aperçu",
					indicator: "red",
				});
			}
		},
	});
}

function show_preview_dialog(previews) {
	let html = '<div style="font-size: 14px;">';

	previews.forEach((preview, index) => {
		html += `
			<div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;">
				<p><strong>Client:</strong> ${preview.customer}</p>
				<p><strong>Article:</strong> ${preview.item}</p>
				<p><strong>Prix:</strong> ${preview.price}€</p>
				<div style="background: #f8f9fa; padding: 10px; border-radius: 3px;">
					<strong>Message:</strong><br>
					${preview.message.replace(/\n/g, "<br>")}
				</div>
			</div>
		`;
	});

	html += "</div>";

	frappe.msgprint({
		title: __("Aperçu Messages SMS"),
		message: html,
		indicator: "blue",
	});
}

function update_dashboard(frm) {
	if (frm.doc.enabled) {
		frm.dashboard.add_comment(__("Campagne activée"), "green", true);
	} else {
		frm.dashboard.add_comment(__("Campagne désactivée"), "red", true);
	}

	if (frm.doc.sms_sent_count > 0) {
		frm.dashboard.add_comment(__(`${frm.doc.sms_sent_count} SMS envoyés`), "blue", true);
	}
}

function refresh_totals(frm) {
	if (frm.doc.pricing_items && frm.doc.pricing_items.length > 0) {
		calculate_campaign_totals(frm);
	}
}

function setup_filters(frm) {
	// Filtres pour les clients
	frm.set_query("customer", "pricing_items", function () {
		return {
			filters: {
				disabled: 0,
			},
		};
	});

	// Filtres pour les articles
	frm.set_query("item_code", "pricing_items", function () {
		return {
			filters: {
				disabled: 0,
				is_sales_item: 1,
			},
		};
	});
}

// Fonctions utilitaires globales

function format_phone_number(phone) {
	if (!phone) return phone;

	let cleaned = phone.replace(/[^\d+]/g, "");

	if (cleaned.startsWith("0")) {
		cleaned = "+33" + cleaned.substring(1);
	} else if (!cleaned.startsWith("+")) {
		cleaned = "+33" + cleaned;
	}

	return cleaned;
}

function generate_sms_preview(template, item) {
	if (!template || !item) return "";

	return template
		.replace(/{{customer_name}}/g, item.customer_name || "Client Test")
		.replace(/{{item_name}}/g, item.item_name || "Article Test")
		.replace(/{{final_price}}/g, item.final_price || "0")
		.replace(/{{currency}}/g, item.currency || "EUR");
}

function validate_sms_template(template) {
	if (!template) return;

	const required_vars = ["{{customer_name}}", "{{item_name}}", "{{final_price}}"];
	const missing = required_vars.filter((v) => !template.includes(v));

	if (missing.length > 0) {
		frappe.show_alert({
			message: __(`Variables manquantes: ${missing.join(", ")}`),
			indicator: "orange",
		});
	}

	if (template.length > 160) {
		frappe.show_alert({
			message: __(`Message long (${template.length} caractères)`),
			indicator: "orange",
		});
	}
}

async function get_item_valuation_rate(item_code) {
	try {
		const response = await frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Stock Ledger Entry",
				filters: {
					item_code: item_code,
					valuation_rate: [">", 0],
				},
				fields: ["valuation_rate"],
				order_by: "posting_date desc, posting_time desc",
				limit_start: 0,
				limit_page_length: 1,
			},
		});

		if (response.message && response.message.length > 0) {
			return response.message[0].valuation_rate;
		}
		return 0;
	} catch (error) {
		console.error("Erreur récupération taux valorisation:", error);
		return 0;
	}
}
