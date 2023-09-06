// Copyright (c) 2023, KAINOTOMO PH LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Template', {
	refresh: function(frm) {
		frm.fields_dict['tax_account_head'].get_query = function(doc, cdt, cdn) {
            return {
                filters: [
                    ['Account', 'account_type', '=', 'Tax']
                ]
            };
        };

		frm.fields_dict['expense_account'].get_query = function(doc, cdt, cdn) {
            return {
                filters: [
                    ['Account', 'root_type', '=', 'Expense']
                ]
            };
        };

		frm.add_custom_button(__('Generate YML'), function () {
			frappe.call({
				method: "invoice2erpnext.invoice2erpnext.doctype.invoice_template.invoice_template.generate_yml",
				args: {
					doc: frm.doc,
				},
				callback: function (response) {
					if (response.message.errors) {
						frappe.msgprint("Something went wrong.", 'Error');
					} else {
						frm.set_value('yml', response.message);
						frm.refresh_field('yml');
					}
				}
			});
		});
	}
});
