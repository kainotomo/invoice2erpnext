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
        # Initialize result structure
        result = {
            "success": True,
            "erpnext_docs": []
        }
        
        try:
            # Get vendor information
            vendor_name = extracted_doc.get("VendorName", {}).get("valueString", "").replace("\n", " ").strip()
            if not vendor_name:
                frappe.throw("Vendor name not found in extracted document")
            
            # 1. Create Supplier document
            vendor_address = extracted_doc.get("VendorAddress", {}).get("valueAddress", {})
            supplier_doc = {
                "doctype": "Supplier",
                "supplier_name": vendor_name,
                "supplier_group": "All Supplier Groups",  # Default value
                "supplier_type": "Company",  # Default value
                "country": vendor_address.get("countryRegion", "Cyprus"),
                "address_line1": vendor_address.get("streetAddress", ""),
                "city": vendor_address.get("city", ""),
                "pincode": vendor_address.get("postalCode", "")
            }
            result["erpnext_docs"].append(supplier_doc)
            
            # 2. Create Item documents and prepare items for invoice
            items = extracted_doc.get("Items", {}).get("valueArray", [])
            invoice_items = []
            
            for idx, item in enumerate(items):
                item_data = item.get("valueObject", {})
                description = item_data.get("Description", {}).get("valueString", "")
                
                # Generate item code based on description
                description_first_line = description.split("\n")[0] if description else f"Item {idx+1}"
                item_code = f"INV-{extracted_doc.get('InvoiceId', {}).get('valueString', '')}-{idx+1}"
                
                amount = item_data.get("Amount", {}).get("valueCurrency", {}).get("amount", 0)
                
                item_doc = {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": description_first_line[:140],
                    "description": description,
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,  # Assuming service item
                    "is_purchase_item": 1
                }
                result["erpnext_docs"].append(item_doc)
                
                # Prepare item for purchase invoice
                invoice_item = {
                    "item_code": item_code,
                    "qty": 1,
                    "rate": amount,
                    "amount": amount,
                    "description": description,
                    "uom": "Nos"
                }
                invoice_items.append(invoice_item)
            
            # 3. Create Purchase Invoice document
            invoice_date = extracted_doc.get("InvoiceDate", {}).get("valueDate", "")
            currency = extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("currencyCode", "EUR")
            bill_no = extracted_doc.get("InvoiceId", {}).get("valueString", "")
            
            purchase_invoice = {
                "doctype": "Purchase Invoice",
                "title": f"Invoice {bill_no}",
                "supplier": vendor_name,
                "bill_no": bill_no,
                "bill_date": invoice_date,
                "posting_date": invoice_date,
                "currency": currency,
                "conversion_rate": 1,
                "items": invoice_items,
            }
            
            # Add taxes if available
            subtotal = extracted_doc.get("SubTotal", {}).get("valueCurrency", {}).get("amount", 0)
            total_tax = extracted_doc.get("TotalTax", {}).get("valueCurrency", {}).get("amount", 0)

            if subtotal and total_tax:
                tax_rate = 0
                
                # Try to get the tax rate from tax details first
                tax_details = extracted_doc.get("TaxDetails", {}).get("valueArray", [])
                for tax in tax_details:
                    tax_data = tax.get("valueObject", {})
                    if "Rate" in tax_data:
                        tax_rate_str = tax_data.get("Rate", {}).get("valueString", "0%").replace("%", "")
                        try:
                            tax_rate = float(tax_rate_str)
                            break
                        except ValueError:
                            pass
                
                # If no tax rate found in details, calculate it
                if tax_rate == 0 and subtotal > 0:
                    tax_rate = round((total_tax / subtotal) * 100, 2)
                
                # Get the VAT account from settings
                settings = frappe.get_doc("Invoice2Erpnext Settings")
                vat_account = settings.vat_account or "VAT - TC"  # Default fallback if not set
                
                purchase_invoice["taxes"] = [{
                    "charge_type": "On Net Total",
                    "account_head": vat_account,
                    "description": f"VAT {tax_rate}%",
                    "rate": tax_rate
                }]
            
            result["erpnext_docs"].append(purchase_invoice)
            
            return result
        
        except Exception as e:
            frappe.log_error(f"Error transforming extracted document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

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
