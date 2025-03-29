frappe.listview_settings['Purchase Invoice'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Upload'), function() {
            new frappe.ui.FileUploader({
                as_dataurl: false,
                allow_multiple: true,
                on_success: function(file_doc) {
                    create_purchase_invoice_from_files(file_doc, listview);
                }
            });
        });
    }
};

// Function to process the uploaded files and create doc2sys_items
function create_purchase_invoice_from_files(file_docs, listview) {
    if (!Array.isArray(file_docs)) {
        file_docs = [file_docs]; // Convert to array if single file
    }
    
    if (file_docs.length === 0) return;
    
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
                file_doc_name: file_doc.name
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