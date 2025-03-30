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
from typing import Dict, Any, List
from invoice2erpnext.utils import format_currency_value  # Import the utility function


class Invoice2ErpnextLog(Document):
    @frappe.whitelist()
    def create_purchase_invoice(self):
        # Check if the message field contains a valid JSON string
        try:
            response_data = json.loads(self.response)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format in message field."))
        # Check if the message contains the expected structure
        if not isinstance(response_data, dict) or "message" not in response_data:
            frappe.throw(_("Invalid message structure in message field."))
        # Extract the relevant data from the message
        message = response_data["message"]
        if not isinstance(message, dict) or "success" not in message:
            frappe.throw(_("Invalid message structure in message field."))
        if not message["success"]:
            frappe.throw(_("API call was not successful."))
        if not isinstance(message, dict) or "cost" not in message:
            frappe.throw(_("Invalid message structure in message field."))
        
        self.cost = message["cost"]
        
        if not isinstance(message, dict) or "extracted_data" not in message:
            frappe.throw(_("Invalid message structure in extracted_data field."))
        extracted_data = json.loads(message["extracted_data"])
        result = self._transform_purchase_invoice(extracted_data)
        if not result.get("success"):
            frappe.throw(_("Transformation failed."))
        erpnext_docs = result.get("erpnext_docs", [])
        if not erpnext_docs:
            frappe.throw(_("No documents to create."))
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
        for doc in erpnext_docs:
            doc_type = doc.get("doctype")
            if doc_type == "Purchase Invoice":
                created_docs.append(doc.get("title"))
        if created_docs:
            self.created_docs = ", ".join(created_docs)

        # Update the status to "Completed"
        self.status = "Success"
        self.save()

    def _transform_purchase_invoice(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform generic invoice data to ERPNext Purchase Invoice format"""
        # Create ERPNext-specific document structure
        erpnext_docs = []
        
        # Create a Supplier doc if supplier information is available
        if extracted_data.get("supplier_name"):
            supplier_doc = {
                "doctype": "Supplier",
                "supplier_name": extracted_data.get("supplier_name"),
                "supplier_type": "Company",  # Default value
                "supplier_group": "All Supplier Groups",  # Default value
            }
            
            # Add email if available
            if extracted_data.get("supplier_email"):
                supplier_doc["email_id"] = extracted_data.get("supplier_email")
                
            # Add phone if available  
            if extracted_data.get("supplier_phone"):
                supplier_doc["mobile_no"] = extracted_data.get("supplier_phone")
                
            erpnext_docs.append(supplier_doc)
        
        # Create Item docs for each line item
        actual_items = []
        items = extracted_data.get("items", [])
        for item in items:
            # Skip special entries like totals or payment methods
            if item.get("description") and not any(keyword in item.get("description", "").lower() 
                                                  for keyword in ["total", "credit card", "payment"]):
                item_doc = {
                    "doctype": "Item",
                    "item_name": item.get("description")[:140],
                    "item_code": item.get("item_code") or item.get("description")[:140],
                    "item_group": "All Item Groups",  # Default value
                    "stock_uom": "Nos",  # Default value
                    "is_stock_item": 0,
                    "is_purchase_item": 1
                }
                erpnext_docs.append(item_doc)
                actual_items.append(item)
        
        # Create Purchase Invoice doc
        invoice_doc = {
            "doctype": "Purchase Invoice",
            "title": extracted_data.get("supplier_name", "Unknown"),
            "supplier": extracted_data.get("supplier_name"),
            "posting_date": extracted_data.get("invoice_date") or extracted_data.get("due_date"),
            "bill_no": extracted_data.get("invoice_number"),
            "due_date": extracted_data.get("due_date"),
            "items": [],
            "taxes": []
        }
        
        # Set currency if available
        if extracted_data.get("currency"):
            invoice_doc["currency"] = extracted_data.get("currency")
        
        # Add items to the invoice (only actual product items)
        for item in actual_items:
            invoice_item = {
                "item_code": item.get("item_code") or item.get("description"),
                "item_name": item.get("description")[:140],
                "description": item.get("description"),
                "qty": item.get("quantity", 1),
                "rate": item.get("unit_price", 0),
                "amount": item.get("amount", 0)
            }
            invoice_doc["items"].append(invoice_item)
        
        # Add tax information if available
        if extracted_data.get("tax_amount"):
            # Get the VAT account from settings or use a default value
            vat_account = frappe.db.get_value("Invoice2Erpnext Settings", None, "vat_account") or "VAT - XXX"
            
            tax_row = {
                "doctype": "Purchase Taxes and Charges",
                "charge_type": "Actual",
                "account_head": vat_account,
                "description": "Tax",
                "tax_amount": extracted_data.get("tax_amount", 0),
                "category": "Total",
                "add_deduct_tax": "Add"
            }
            invoice_doc["taxes"].append(tax_row)
        
        # Set total amounts
        if extracted_data.get("subtotal"):
            invoice_doc["net_total"] = extracted_data.get("subtotal")
        
        if extracted_data.get("total_amount"):
            invoice_doc["grand_total"] = extracted_data.get("total_amount")
            invoice_doc["rounded_total"] = extracted_data.get("total_amount")
                
        erpnext_docs.append(invoice_doc)

        # Define doctype priorities - lower number = higher priority
        doctype_priority = {
            "Supplier": 1,
            "Item": 2,
            "Purchase Invoice": 3,
        }
        
        # Sort items by doctype priority to ensure dependencies are created first
        # Items consistently have a nested "doc" structure in the new format
        sorted_items = sorted(erpnext_docs, key=lambda x: doctype_priority.get(
            x.get("doctype", ""), 999
        ))
        
        return {
            "success": True,
            "erpnext_docs": sorted_items
        }

@frappe.whitelist()
def create_purchase_invoice_from_file(file_doc_name):
    """Create a Purchase Invoice from an existing File document"""
    file_doc = frappe.get_doc("File", file_doc_name)
    if not file_doc:
        frappe.throw(_("File not found"))
    
    # Create new Invoice2Erpnext Log
    doc = frappe.new_doc("Invoice2Erpnext Log")
    doc.single_file = file_doc.file_url
    doc.insert()
    frappe.db.commit()

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
            doc.response = json.dumps(response_data)
            
            # Check if the response has a success message in the expected format
            message = response_data.get("message", {})
            if isinstance(message, dict) and message.get("success"):
                doc.status = "Retrieved"
                doc.message = _("Response retrieved successfully.")
                doc.save()
                frappe.db.commit()
                doc.reload()
                doc.create_purchase_invoice()
            else:
                # Handle error response with proper structure
                error_msg = message.get("message") if isinstance(message, dict) else str(message)
                doc.status = "Error"
                doc.message = f"API Error: {error_msg}"
        else:
            doc.status = "Error"
            doc.message = f"HTTP Error: {response.status_code} - {response.text}"
    
    except Exception as e:
        doc.status = "Error"
        doc.message = f"Connection Error: {str(e)}"
    
    doc.save()
    return doc.name
