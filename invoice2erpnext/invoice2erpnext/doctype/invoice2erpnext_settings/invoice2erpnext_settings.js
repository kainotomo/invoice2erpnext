// Copyright (c) 2025, KAINOTOMO PH LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice2Erpnext Settings', {
    refresh: function(frm) {
        // Add a button to test the connection
        frm.add_custom_button(__('Test Connection'), function() {
            frm.call({
                doc: frm.doc,
                method: 'test_connection',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: __('Connection successful! Credits: {0}', [r.message.credits])
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: r.message ? r.message.message : __('Connection failed')
                        });
                    }
                    // Reload the form to reflect updated values
                    frm.reload_doc();
                }
            });
        });
        
    },
});
