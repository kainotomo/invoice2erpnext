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
        new_doc = None
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
        if new_doc:
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
        # Define constants
        ROUNDING_TOLERANCE = 0.05
        
        # Initialize result structure
        result = {
            "success": True,
            "erpnext_docs": []
        }
        
        # Define helper function for standardizing decimal precision
        def round_amount(amount):
            """Standardize decimal precision for monetary values"""
            if amount is None:
                return 0
            try:
                return round(float(amount), 2)
            except (ValueError, TypeError):
                return 0
        
        try:
            # Document quality score tracking
            document_score = 0
            
            bill_no = extracted_doc.get("InvoiceId", {}).get("valueString", "")
            if bill_no:
                document_score += 20
            
            # Get vendor information
            vendor_name = extracted_doc.get("VendorName", {}).get("valueString", "").replace("\n", " ").strip()
            if not vendor_name:
                frappe.throw("Vendor name not found in extracted document")
            else:
                document_score += 20
            
            # 1. Create Supplier document
            vendor_address = extracted_doc.get("VendorAddress", {}).get("valueAddress", {})
            vendor_tax_id = extracted_doc.get("VendorTaxId", {}).get("valueString", "")

            supplier_doc = {
                "doctype": "Supplier",
                "supplier_name": vendor_name,
                "supplier_group": "All Supplier Groups",  # Default value
                "supplier_type": "Company",  # Default value
                "country": vendor_address.get("countryRegion", "Cyprus"),
                "address_line1": vendor_address.get("streetAddress", ""),
                "city": vendor_address.get("city", ""),
                "pincode": vendor_address.get("postalCode", ""),
                "tax_id": vendor_tax_id  # Add the tax ID
            }
            result["erpnext_docs"].append(supplier_doc)
            
            # 2. Create Item documents and prepare items for invoice
            items = extracted_doc.get("Items", {}).get("valueArray", [])
            if items:
                document_score += 20
                
            invoice_items = []
            
            # Check for currency consistency among items
            invoice_currency = extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("currencyCode", "EUR")
            item_currencies = set()
            for item in items:
                item_currency = item.get("valueObject", {}).get("Amount", {}).get("valueCurrency", {}).get("currencyCode")
                if item_currency:
                    item_currencies.add(item_currency)
            
            if item_currencies and any(curr != invoice_currency for curr in item_currencies):
                frappe.log_error(f"Currency mismatch: Invoice is {invoice_currency} but items have {item_currencies} in invoice {bill_no}")
            
            for idx, item in enumerate(items):
                item_data = item.get("valueObject", {})
                description = item_data.get("Description", {}).get("valueString", "")
                
                # Get product code if available, otherwise generate one
                product_code = item_data.get("ProductCode", {}).get("valueString", "")
                if product_code:
                    item_code = f"{product_code}-{bill_no}"
                else:
                    # Generate item code based on description with hash for uniqueness
                    import hashlib
                    desc_hash = hashlib.md5(description.encode()).hexdigest()[:8] if description else ""
                    item_code = f"INV-{bill_no}-{idx+1}-{desc_hash}"
                
                # Get item details with standardized precision
                amount = round_amount(item_data.get("Amount", {}).get("valueCurrency", {}).get("amount", 0))
                unit_price = round_amount(item_data.get("UnitPrice", {}).get("valueCurrency", {}).get("amount", 0))
                quantity = item_data.get("Quantity", {}).get("valueNumber", 1) or 1  # Ensure quantity is never zero
                
                item_doc = {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": description.split("\n")[0][:140] if description else f"Item {idx+1}",
                    "description": description,
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,  # Assuming service item
                    "is_purchase_item": 1
                }
                result["erpnext_docs"].append(item_doc)
                
                # Handle negative amounts (credits/refunds)
                is_credit = amount < 0
                
                # Calculate discount or markup if any
                if unit_price and quantity and amount:
                    calculated_amount = round_amount(unit_price * quantity)
                    
                    # Handle both discount and markup scenarios
                    if abs(calculated_amount - amount) > ROUNDING_TOLERANCE:  # Use constant for tolerance
                        # Use the final amount to determine the effective rate
                        invoice_item = {
                            "item_code": item_code,
                            "qty": abs(quantity),  # Always positive quantity
                            "rate": amount / quantity if quantity else amount,  # Add division by zero protection
                            "amount": amount,
                            "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                            "uom": "Nos"
                        }
                    else:
                        # No discount/markup - use unit price as is
                        invoice_item = {
                            "item_code": item_code,
                            "qty": abs(quantity),  # Always positive quantity
                            "rate": unit_price * (-1 if is_credit else 1),
                            "amount": amount,
                            "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                            "uom": "Nos"
                        }
                elif unit_price and quantity:
                    # We have unit price and quantity but no amount
                    calculated_amount = round_amount(unit_price * quantity)
                    invoice_item = {
                        "item_code": item_code,
                        "qty": abs(quantity),
                        "rate": unit_price * (-1 if is_credit else 1),
                        "amount": calculated_amount * (-1 if is_credit else 1),
                        "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                        "uom": "Nos"
                    }
                elif amount:
                    # We only have the amount
                    invoice_item = {
                        "item_code": item_code,
                        "qty": abs(quantity),
                        "rate": amount / quantity if quantity else amount,  # Add division by zero protection
                        "amount": amount,
                        "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                        "uom": "Nos"
                    }
                else:
                    # Fallback if no pricing details at all
                    invoice_item = {
                        "item_code": item_code,
                        "qty": abs(quantity),
                        "rate": 0,
                        "amount": 0,
                        "description": description,
                        "uom": "Nos"
                    }
                    frappe.log_error(f"No pricing information for item {item_code} in invoice {bill_no}")
    
                invoice_items.append(invoice_item)
            
            # 3. Create Purchase Invoice document
            invoice_date = extracted_doc.get("InvoiceDate", {}).get("valueDate", "")
            if invoice_date:
                document_score += 20
                
                # Validate date format if needed
                try:
                    # Simple validation - just check if it's in expected YYYY-MM-DD format
                    if len(invoice_date.split('-')) != 3:
                        frappe.log_error(f"Invalid date format in invoice {bill_no}: {invoice_date}")
                except:
                    pass
                    
            currency = extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("currencyCode", "EUR")
            
            # Get payment terms if available
            payment_terms = extracted_doc.get("PaymentTerm", {}).get("valueString", "")
            
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
                "payment_terms_template": payment_terms if frappe.db.exists("Payment Terms Template", payment_terms) else "",
            }
            
            # Check for document-level discount or markup
            subtotal = round_amount(extracted_doc.get("SubTotal", {}).get("valueCurrency", {}).get("amount", 0))
            invoice_total = round_amount(extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("amount", 0))
            total_tax = round_amount(extracted_doc.get("TotalTax", {}).get("valueCurrency", {}).get("amount", 0))
            total_discount = round_amount(extracted_doc.get("TotalDiscount", {}).get("valueCurrency", {}).get("amount", 0))
            
            # Calculate expected invoice total and validate against extracted total
            expected_total = round_amount(subtotal + total_tax - total_discount)
            if invoice_total > 0 and abs(expected_total - invoice_total) > ROUNDING_TOLERANCE:
                subtotal = invoice_total  - total_tax + total_discount
            elif expected_total > 0 and invoice_total == 0:
                # If no invoice total was extracted but we can calculate it
                invoice_total = expected_total

            # Instead of using line items total, prioritize extracted totals
            calculated_line_total = round_amount(sum(item.get("amount", 0) for item in invoice_items))
            if subtotal > 0 and abs(calculated_line_total - subtotal) > ROUNDING_TOLERANCE:
                # There's a discrepancy - adjust line items to match the invoice total
                adjustment_factor = subtotal / calculated_line_total if calculated_line_total != 0 else 1
                
                # Apply adjustment to all line items proportionally
                for item in invoice_items:
                    original_amount = item.get("amount", 0)
                    adjusted_amount = round_amount(original_amount * adjustment_factor)
                    item["amount"] = adjusted_amount
                    # Recalculate rate based on new amount
                    item["rate"] = round_amount(adjusted_amount / item["qty"] if item["qty"] else adjusted_amount)
                
                # Log the adjustment
                frappe.log_error(f"Adjusted line items in invoice {bill_no}: Original total {calculated_line_total}, adjusted to {invoice_total}")
            
            # Add taxes with the corrected amount
            if total_tax:
                # Get the VAT account from settings with better error handling
                try:
                    settings = frappe.get_doc("Invoice2Erpnext Settings")
                    vat_account = settings.vat_account or "VAT - TC"
                except Exception as e:
                    frappe.log_error(f"Error fetching Invoice2Erpnext Settings: {str(e)}")
                    vat_account = "VAT - TC"

                purchase_invoice["taxes"] = [{
                    "charge_type": "Actual",
                    "account_head": vat_account,
                    "description": "VAT",
                    "tax_amount": total_tax,
                    "included_in_print_rate": 0  # Tax is NOT included (since we extracted it)
                }]
            
            result["erpnext_docs"].append(purchase_invoice)
            
            # Log document quality score
            if document_score < 80:
                frappe.log_error(f"Low-quality document extraction (score: {document_score}/100) for invoice {bill_no}")
            
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
