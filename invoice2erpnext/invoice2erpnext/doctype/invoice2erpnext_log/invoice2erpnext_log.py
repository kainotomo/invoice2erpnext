# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests
import json
from urllib.parse import urljoin


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
    
    # Prepare form data
    form_data = {
        "file": file_doc.file_url,
        "is_private": 1
    }
    
    try:
        # Make the API call
        response = requests.post(
            api_url,
            headers=headers,
            data=form_data
        )
        
        # Store response as a message instead of using api_response field
        response_text = response.text
        
        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            
            # Store full response as a JSON string in the message field
            frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", json.dumps(response_data))
            
            if response_data.get("success"):
                frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Success")
                
                # If doc2sys_item is in the response, store it
                if response_data.get("doc2sys_item"):
                    frappe.db.set_value("Invoice2Erpnext Log", doc.name, "doc2sys_item", 
                                         response_data.get("doc2sys_item"))
            else:
                error_msg = response_data.get("message", "API returned error")
                frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Error")
                frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", 
                                     f"API Error: {error_msg}")
        else:
            frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Error")
            frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", 
                                 f"HTTP Error: {response.status_code}")
    
    except Exception as e:
        frappe.log_error(f"API Connection Error: {str(e)}", "Invoice2ERPNext")
        frappe.db.set_value("Invoice2Erpnext Log", doc.name, "status", "Error")
        frappe.db.set_value("Invoice2Erpnext Log", doc.name, "message", f"Connection Error: {str(e)}")
    
    return doc.name