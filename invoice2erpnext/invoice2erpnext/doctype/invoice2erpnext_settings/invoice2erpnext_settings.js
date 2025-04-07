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
        
        // Populate the available_credits HTML field
        frappe.call({
            method: "invoice2erpnext.invoice2erpnext.doctype.invoice2erpnext_settings.invoice2erpnext_settings.get_available_credits",
            callback: function(r) {
                if (r.message && r.message.value !== undefined) {
                    // Get credits value
                    let credits = r.message.value;
                    
                    // Format manually without using frappe.format for currency
                    // This avoids the right-alignment issue
                    let currencySymbol = frappe.boot.sysdefaults.currency_symbol || '€';
                    let formattedValue = parseFloat(credits).toFixed(2).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                    let formattedCredits = currencySymbol + ' ' + formattedValue;
                    
                    // Create HTML using Frappe's standard classes with explicit left alignment
                    let html = `
                        <div class="frappe-card p-3">
                            <div class="value text-xl bold text-primary text-center" style="text-align: left !important;">${formattedCredits}</div>
                            <div class="mt-3">
                                <a href="https://kainotomo.com/invoice2erpnext/shop" target="_blank" 
                                   class="btn btn-primary btn-sm">Purchase Credits</a>
                            </div>
                        </div>
                    `;
                    
                    // Set the HTML in the available_credits field
                    $(frm.fields_dict.available_credits.wrapper).html(html);
                } else {
                    // Handle error or zero credits case
                    let currencySymbol = frappe.boot.sysdefaults.currency_symbol || '€';
                    let formattedCredits = currencySymbol + ' 0.00';
                    
                    $(frm.fields_dict.available_credits.wrapper).html(`
                        <div class="frappe-card p-3">
                            <div class="section-head text-muted">AVAILABLE CREDITS</div>
                            <div class="value text-xl bold text-muted text-left" style="text-align: left !important;">${formattedCredits}</div>
                            <div class="mt-3">
                                <a href="https://kainotomo.com/invoice2erpnext/shop" target="_blank" 
                                   class="btn btn-primary btn-sm">Purchase Credits</a>
                            </div>
                        </div>
                    `);
                }
            }
        });
    },
});
