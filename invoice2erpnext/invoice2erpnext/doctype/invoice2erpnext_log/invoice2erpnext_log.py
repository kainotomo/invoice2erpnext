# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import json
import os
import mimetypes
from urllib.parse import urljoin
from frappe.utils import get_files_path, get_site_path
from typing import Dict, Any, List
from invoice2erpnext.utils import format_currency_value  # Import the utility function


class Invoice2ErpnextLog(Document):
    @frappe.whitelist()
    def create_purchase_invoice(self):
        # Check if the message field contains a valid JSON string
        try:
            response_data = json.loads(self.response)
        except json.JSONDecodeError:
            frappe.throw("Invalid JSON format in message field.")
        # Check if the message contains the expected structure
        if not isinstance(response_data, dict) or "message" not in response_data:
            frappe.throw("Invalid message structure in message field.")
        # Extract the relevant data from the message
        message = response_data["message"]
        if not isinstance(message, dict) or "success" not in message:
            frappe.throw("Invalid message structure in message field.")
        if not message["success"]:
            frappe.throw("API call was not successful.")
        if not isinstance(message, dict) or "cost" not in message:
            frappe.throw("Invalid message structure in message field.")
        
        self.cost = message["cost"]

        if not isinstance(message, dict) or "extracted_doc" not in message:
            frappe.throw("Invalid message structure in extracted_doc field.")
        extracted_doc = json.loads(message["extracted_doc"])
        result = self._transform_extracted_doc(extracted_doc)
        
        if not result.get("success"):
            frappe.throw("Transformation failed.")
        erpnext_docs = result.get("erpnext_docs", [])
        if not erpnext_docs:
            frappe.throw("No documents to create.")
        # Create each document in ERPNext
        for doc in erpnext_docs:
            doc_type = doc.get("doctype")
            if doc_type:
                # Check if Supplier or Item already exists
                if doc_type == "Supplier" and frappe.db.exists("Supplier", doc.get("supplier_name")):
                    continue  # Skip creation as supplier already exists
                elif doc_type == "Item" and frappe.db.exists("Item", doc.get("item_code")):
                    continue  # Skip creation as item already exists
                elif doc_type == "Purchase Invoice" and doc.get("bill_no") and frappe.db.exists("Purchase Invoice", {"bill_no": doc.get("bill_no")}):
                    continue  # Skip creation as purchase invoice with this bill number already exists

                # Create the document in ERPNext
                new_doc = frappe.new_doc(doc_type)
                for field, value in doc.items():
                    if field != "doctype":
                        new_doc.set(field, value)
                if doc_type == "Purchase Invoice":
                    new_doc.set("set_posting_time", 1)
                # Save the document
                new_doc.insert(ignore_permissions=True)
        # Update the log with the created document names
        created_docs = []
        created_purchase_invoices = []
        for doc in erpnext_docs:
            doc_type = doc.get("doctype")
            if doc_type == "Purchase Invoice":
                # Get the name of the created Purchase Invoice
                invoice_name = new_doc.name
                created_docs.append(doc.get("title"))
                created_purchase_invoices.append(invoice_name)
        
        if created_docs:
            self.created_docs = ", ".join(created_docs)
        
        # Modify the original file to link it to the Purchase Invoice
        if created_purchase_invoices and self.file:
            try:
                file_doc = frappe.get_doc("File", self.file)
                if file_doc:
                    # Update the file to be attached to the Purchase Invoice
                    file_doc.attached_to_doctype = "Purchase Invoice"
                    file_doc.attached_to_name = created_purchase_invoices[0]  # Attach to the first invoice
                    file_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error attaching file to Purchase Invoice: {str(e)}")

        # Update the status to "Completed"
        self.status = "Success"
        self.save()

    def _transform_extracted_doc(self, extracted_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform generic invoice data to ERPNext format"""
        return extracted_doc

@frappe.whitelist()
def create_purchase_invoice_from_file(file_doc_name):
    """Create a Purchase Invoice from an existing File document"""

    file_doc = frappe.get_doc("File", file_doc_name)
    if not file_doc:
        frappe.throw("File not found")
    
    # Create new Invoice2Erpnext Log
    doc = frappe.new_doc("Invoice2Erpnext Log")
    doc.file = file_doc_name
    doc.insert()
    frappe.db.commit()

    # Get settings for API connection
    settings = frappe.get_doc("Invoice2Erpnext Settings")
    if not settings:
        frappe.throw("Invoice2Erpnext Settings not found")
    
    # Get base URL, API key and API secret
    base_url = settings.BASE_URL
    api_key = settings.get('api_key')
    api_secret = settings.get_password('api_secret')
    
    # Set up API headers with authentication
    headers = {
        "Authorization": f"token {api_key}:{api_secret}"
    }
    
    # Prepare the API endpoint
    endpoint = "/api/method/doc2sys.doc2sys.doctype.doc2sys_item.doc2sys_item.upload_and_create_item"
    api_url = urljoin(base_url, endpoint)

    try:
        # Get the file from the filesystem
        file_name = os.path.basename(file_doc.file_url)
        # Handle both public and private files
        if file_doc.is_private:
            file_path = os.path.join(get_files_path(is_private=True), file_doc.file_name)
        else:
            file_path = os.path.join(get_files_path(), file_doc.file_name)
        
        if not os.path.exists(file_path):
            frappe.throw("File not found on disk: {}").format(file_path)
        
        # Determine content type based on file extension
        content_type, _ = mimetypes.guess_type(file_name)
        if not content_type:
            content_type = 'application/octet-stream'  # Default content type
        
        # Open the file in binary mode and create the files object for multipart/form-data
        with open(file_path, 'rb') as file_content:
            files = {
                'file': (file_name, file_content, content_type)
            }
            
            # Prepare form data
            form_data = {
                "is_private": "1"
            }
            
            # Make the API call with multipart/form-data
            response = requests.post(
                api_url,
                headers=headers,
                files=files,
                data=form_data
            )
        
        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            doc.response = json.dumps(response_data)
            
            # Check if the response has a success message in the expected format
            message = response_data.get("message", {})
            if isinstance(message, dict) and message.get("success"):
                doc.status = "Retrieved"
                doc.message = "Response retrieved successfully."
                doc.save()
                frappe.db.commit()
                doc.reload()
                doc.create_purchase_invoice()
            else:
                # Handle error response with proper structure
                error_msg = message.get("message") if isinstance(message, dict) else str(message)
                doc.status = "Error"
                doc.message = f"API Error: {error_msg}"
                frappe.msgprint(f"Error: {error_msg}<br>See <a href='/app/invoice2erpnext-log/{doc.name}'>Log #{doc.name}</a> for details")
        else:
            doc.status = "Error"
            doc.message = f"HTTP Error: {response.status_code} - {response.text}"
            frappe.msgprint(f"Error: {response.status_code} - {response.text}<br>See <a href='/app/invoice2erpnext-log/{doc.name}'>Log #{doc.name}</a> for details")
    
    except Exception as e:
        doc.status = "Error"
        doc.message = f"Connection Error: {str(e)}"
        frappe.msgprint(f"Error: {str(e)}<br>See <a href='/app/invoice2erpnext-log/{doc.name}'>Log #{doc.name}</a> for details")
    
    doc.save()
    return doc.name
