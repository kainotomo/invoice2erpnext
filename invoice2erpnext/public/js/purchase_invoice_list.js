frappe.listview_settings['Purchase Invoice'] = {
    onload: function(listview) {
        // Check if integration is enabled before showing the upload button
        frappe.xcall('invoice2erpnext.utils.check_settings_enabled')
            .then(enabled => {
                if (enabled) {
                    // Add the upload option under a dropdown menu
                    listview.page.add_menu_item(__('Upload (Auto)'), function() {
                        new frappe.ui.FileUploader({
                            as_dataurl: false,
                            allow_multiple: true,
                            on_success: function(file_doc) {
                                create_purchase_invoice_from_files(file_doc, listview, 'auto');
                            }
                        });
                    });
                    listview.page.add_menu_item(__('Upload (Manual)'), function() {
                        new frappe.ui.FileUploader({
                            as_dataurl: false,
                            allow_multiple: true,
                            on_success: function(file_doc) {
                                create_purchase_invoice_from_files(file_doc, listview, 'manual');
                            }
                        });
                    });
                }
            })
            .catch(() => {
                // Silently fail - don't show buttons if there's an error
            });
    }
};

// Function to process the uploaded files and create doc2sys_items
function create_purchase_invoice_from_files(file_docs, listview, mode) {
    if (!Array.isArray(file_docs)) {
        file_docs = [file_docs]; // Convert to array if single file
    }
    
    if (file_docs.length === 0) return;
    
    // If manual mode, show dialog to select supplier and item
    if (mode === 'manual') {
        show_supplier_item_dialog(file_docs, listview);
        return;
    }
    
    // Continue with automatic processing for 'auto' mode
    const total = file_docs.length;
    let processed = 0;
    
    // Show progress dialog
    const dialog = new frappe.ui.Dialog({
        title: __('Creating Documents'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'progress_area',
                options: `<div class="progress">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
                <p class="text-muted" style="margin-top: 10px">
                    <span class="processed">0</span> ${__('of')} ${total} ${__('documents created')}
                </p>`
            }
        ]
    });
    
    dialog.show();
    
    // Process files one by one to create doc2sys_items
    function process_next_file(index) {
        if (index >= file_docs.length) {
            // All files processed
            setTimeout(() => {
                dialog.hide();
                frappe.show_alert({
                    message: __(`Created ${processed} documents successfully`),
                    indicator: 'green'
                });
                listview.refresh();
            }, 1000);
            return;
        }
        
        const file_doc = file_docs[index];
        
        // Create doc2sys_item from file
        frappe.call({
            method: 'invoice2erpnext.invoice2erpnext.doctype.invoice2erpnext_log.invoice2erpnext_log.create_purchase_invoice_from_file',
            args: {
                file_doc_name: file_doc.name,
                mode: mode
            },
            callback: function(r) {
                processed++;
                
                // Update progress
                const percent = (processed / total) * 100;
                dialog.$wrapper.find('.progress-bar').css('width', percent + '%');
                dialog.$wrapper.find('.processed').text(processed);
                
                // Process next file
                process_next_file(index + 1);
            }
        });
    }
    
    // Start processing files
    process_next_file(0);
}

// Function to show dialog for supplier and item selection
function show_supplier_item_dialog(file_docs, listview) {
    if (file_docs.length === 0) return;
    
    // Create a dialog for supplier and item selection
    const dialog = new frappe.ui.Dialog({
        title: __('Select Supplier and Item'),
        fields: [
            {
                label: __('Supplier'),
                fieldname: 'supplier',
                fieldtype: 'Link',
                options: 'Supplier',
                reqd: 1,
                get_query: function() {
                    return {
                        filters: {
                            'disabled': 0
                        }
                    };
                }
            },
            {
                label: __('Item'),
                fieldname: 'item',
                fieldtype: 'Link',
                options: 'Item',
                reqd: 1,
                get_query: function() {
                    return {
                        filters: {
                            'disabled': 0,
                            'is_purchase_item': 1
                        }
                    };
                }
            }
        ],
        primary_action_label: __('Create'),
        primary_action: function(values) {
            dialog.hide();
            
            // Start processing with manual selection
            process_manual_files(file_docs, listview, values.supplier, values.item);
        }
    });
    
    dialog.show();
}

// Function to process files with manual supplier and item selection
function process_manual_files(file_docs, listview, supplier, item) {
    const total = file_docs.length;
    let processed = 0;
    
    // Show progress dialog
    const progress_dialog = new frappe.ui.Dialog({
        title: __('Creating Documents'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'progress_area',
                options: `<div class="progress">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
                <p class="text-muted" style="margin-top: 10px">
                    <span class="processed">0</span> ${__('of')} ${total} ${__('documents created')}
                </p>`
            }
        ]
    });
    
    progress_dialog.show();
    
    // Process files one by one to create doc2sys_items
    function process_next_file(index) {
        if (index >= file_docs.length) {
            // All files processed
            setTimeout(() => {
                progress_dialog.hide();
                frappe.show_alert({
                    message: __(`Created ${processed} documents successfully`),
                    indicator: 'green'
                });
                listview.refresh();
            }, 1000);
            return;
        }
        
        const file_doc = file_docs[index];
        
        // Create doc2sys_item from file with manual selections
        frappe.call({
            method: 'invoice2erpnext.invoice2erpnext.doctype.invoice2erpnext_log.invoice2erpnext_log.create_purchase_invoice_from_file',
            args: {
                file_doc_name: file_doc.name,
                mode: 'manual',
                supplier: supplier,
                item: item
            },
            callback: function(r) {
                processed++;
                
                // Update progress
                const percent = (processed / total) * 100;
                progress_dialog.$wrapper.find('.progress-bar').css('width', percent + '%');
                progress_dialog.$wrapper.find('.processed').text(processed);
                
                // Process next file
                process_next_file(index + 1);
            }
        });
    }
    
    // Start processing files
    process_next_file(0);
}