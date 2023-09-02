// Copyright (c) 2023, KAINOTOMO PH LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice File', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Sales Invoice': 'Sales Invoice'
		}
	},
	refresh: function(frm) {
		if (frm.doc.html_table) {
			frm.set_df_property("html_render", "options", frm.doc.html_table);
			frm.add_custom_button(__('Purchase Invoice'), function () {
				frappe.confirm('Are you sure you want to proceed?', function () {
					frappe.call({
						method: "invoice2erpnext.invoice2erpnext.doctype.invoice_file.invoice_file.make_purchase_invoice",
						args: {
							source_name: frm.doc.name
						},
						callback: function (response) {
							if (response.message.errors) {
								frappe.msgprint("Something went wrong.", 'Error');
							} else {
								//frappe.set_route(['List', "Purchase Invoice", "Purchase Invoice"], { 'status': 'Draft' })
								frappe.msgprint("Succesfully created document.");
							}
						}
					});
				}, function () {
					// action to perform if No is selected
				});
			}, __('Create'));
		} else {
			frm.set_df_property("html_render", "options", "<p>-</p>");
		}
	},	
});
