// Copyright (c) 2025, KAINOTOMO PH LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Invoice2Erpnext Log", {
    refresh(frm) {
        // Only show the button if the document is saved and has a "Success" status
        if (!frm.is_new() && frm.doc.status === "Success") {
            frm.add_custom_button(__('Create Purchase Invoice'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'create_purchase_invoice',
                    freeze: true,
                    freeze_message: __('Creating Purchase Invoice...'),
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Purchase Invoice created successfully'));
                            frm.refresh();
                        }
                    }
                });
            });
        }
    },
});
