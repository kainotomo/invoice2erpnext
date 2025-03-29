// Copyright (c) 2025, KAINOTOMO PH LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice2Erpnext Settings', {
    refresh: function(frm) {
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.msgprint({
                title: __('Testing Connection'),
                indicator: 'blue',
                message: __('Testing connection to ERPNext API...')
            });
            
            // This will make the API call to test the connection
            frm.call({
                method: 'test_erpnext_connection',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.set_value('credits', r.message.credits);
                        frm.save();
                        
                        frappe.msgprint({
                            title: __('Connection Successful'),
                            indicator: 'green',
                            message: __('Connected successfully! Credits: ') + r.message.credits
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Connection Failed'),
                            indicator: 'red',
                            message: r.message.message || __('Could not connect to ERPNext API')
                        });
                    }
                }
            });
        });
    }
});
