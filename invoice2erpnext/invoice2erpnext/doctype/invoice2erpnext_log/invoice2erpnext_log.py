# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests
import json
import os
import mimetypes
from urllib.parse import urljoin
from frappe.utils import get_files_path, get_site_path


class Invoice2ErpnextLog(Document):
    pass

@frappe.whitelist()
def create_purchase_invoice_from_file(file_doc_name):
    """Create a Purchase Invoice from an existing File document"""
    file_doc = frappe.get_doc("File", file_doc_name)
    if not file_doc:
        frappe.throw(_("File not found"))
    
    # Create new Invoice2Erpnext Log
    doc = frappe.new_doc("Invoice2Erpnext Log")
    doc.insert()
    frappe.db.commit()
    
    frappe.db.set_value("Invoice2Erpnext Log", doc.name, "single_file", file_doc.file_url)

    # Get settings for API connection
    settings = frappe.get_doc("Invoice2Erpnext Settings")
    if not settings:
        frappe.throw(_("Invoice2Erpnext Settings not found"))
    
    # Get base URL, API key and API secret
    base_url = settings.BASE_URL
    api_key = settings.get_password('api_key')
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
            frappe.throw(_("File not found on disk: {}").format(file_path))
        
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
            
            # Store full response as a JSON string in the message field
            frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", json.dumps(response_data))
            
            # Check if the response has a success message in the expected format
            message = response_data.get("message", {})
            if isinstance(message, dict) and message.get("success"):
                frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Success")
            else:
                # Handle error response with proper structure
                error_msg = message.get("message") if isinstance(message, dict) else str(message)
                frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Error")
                frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", 
                                    f"API Error: {error_msg}")
        else:
            frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Error")
            frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", 
                                f"HTTP Error: {response.status_code} - {response.text}")
    
    except Exception as e:
        frappe.log_error(f"API Connection Error: {str(e)}", "Invoice2ERPNext")
        frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Error")
        frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", f"Connection Error: {str(e)}")
    
    return doc.name