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
        """Main entry point for purchase invoice creation - routes to appropriate method based on mode"""
        # Check if we're in manual mode with a specified supplier and item
        if hasattr(self, 'manual_mode') and self.manual_mode == 1:
            return self.create_purchase_invoice_manual()
        else:
            return self.create_purchase_invoice_auto()
            
    def create_purchase_invoice_manual(self):
        """Create a purchase invoice using manually selected supplier and item"""
        try:
            # Get specified supplier and item
            supplier = self.manual_supplier
            item_code = self.manual_item
            
            if not supplier or not item_code:
                frappe.throw("Supplier and Item must be specified for manual mode")
            
            if not frappe.db.exists("Supplier", supplier):
                frappe.throw(f"Supplier {supplier} does not exist")
                
            if not frappe.db.exists("Item", item_code):
                frappe.throw(f"Item {item_code} does not exist")
            
            # Extract basic invoice details from API response if available
            invoice_details = self._extract_invoice_details() if self.response else {}
            
            # Get invoice metadata
            bill_no = invoice_details.get('bill_no', '')
            if not bill_no:
                # Fallback to filename if no bill number from extraction
                file_doc = frappe.get_doc("File", self.file)
                file_name = os.path.basename(file_doc.file_url)
                bill_no = os.path.splitext(file_name)[0]  # Remove file extension
                
            # Get invoice date
            invoice_date = invoice_details.get('invoice_date', frappe.utils.today())
            
            # Get currency
            currency = invoice_details.get('currency', 'EUR')
            
            # Get amount info
            total_amount = invoice_details.get('total_amount', 0)
            total_tax = invoice_details.get('total_tax', 0)
            
            # Calculate net amount
            net_amount = total_amount - total_tax if total_tax else total_amount
            
            # Create the Purchase Invoice
            purchase_invoice = frappe.new_doc("Purchase Invoice")
            purchase_invoice.title = supplier
            purchase_invoice.supplier = supplier
            purchase_invoice.bill_no = bill_no
            purchase_invoice.bill_date = invoice_date
            purchase_invoice.posting_date = invoice_date
            purchase_invoice.currency = currency
            purchase_invoice.conversion_rate = 1
            purchase_invoice.set_posting_time = 1
            
            # Add the selected item properly using proper row creation
            item = purchase_invoice.append("items", {})
            item.item_code = item_code
            item.qty = 1
            item.rate = net_amount
            item.amount = net_amount
            item.uom = frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"
            
            # Add tax if available
            if total_tax:
                vat_account = self._get_vat_account()
                tax = purchase_invoice.append("taxes", {})
                tax.charge_type = "Actual"
                tax.account_head = vat_account
                tax.description = "VAT"
                tax.tax_amount = total_tax
                tax.included_in_print_rate = 0
            
            # Save the document
            purchase_invoice.insert(ignore_permissions=True)
            
            # Update the log and link the file
            self._update_log_and_link_file(purchase_invoice.name)
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error in manual purchase invoice creation: {str(e)}")
            self.status = "Error"
            self.message = f"Manual mode error: {str(e)}"
            self.save()
            return False
    
    def create_purchase_invoice_auto(self):
        """Create purchase invoice using fully automatic extraction"""
        try:
            # Check if the message field contains a valid JSON string
            response_data = json.loads(self.response)
            
            # Validate response structure
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
            result = self._transform_extracted_doc_auto(extracted_doc)
            
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

                    # Create the document in ERPNext
                    new_doc = frappe.new_doc(doc_type)
                    for field, value in doc.items():
                        if field != "doctype":
                            new_doc.set(field, value)
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
            return True
            
        except Exception as e:
            frappe.log_error(f"Error in automatic purchase invoice creation: {str(e)}")
            self.status = "Error"
            self.message = f"Auto mode error: {str(e)}"
            self.save()
            return False

    def _transform_extracted_doc_auto(self, extracted_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Full transformation of extracted document for automatic mode"""
        # Define constants
        ROUNDING_TOLERANCE = 0.05
        
        # Initialize result structure
        result = {
            "success": True,
            "erpnext_docs": []
        }
        
        try:
            # Document quality score tracking
            document_score = 0
            
            # Extract basic invoice information
            bill_no, document_score = self._extract_bill_number(extracted_doc, document_score)
            
            # Get vendor information
            vendor_info = self._extract_vendor_info(extracted_doc, document_score)
            document_score = vendor_info.get('document_score', document_score)
            vendor_name = vendor_info.get('vendor_name', '')
            
            if not vendor_name:
                frappe.throw("Vendor name not found in extracted document")
            
            # 1. Create Supplier document
            supplier_doc = self._create_supplier_doc(vendor_info)
            result["erpnext_docs"].append(supplier_doc)
            
            # 2. Process items
            items_result = self._process_items(extracted_doc, bill_no, document_score)
            document_score = items_result.get('document_score', document_score)
            invoice_items = items_result.get('invoice_items', [])
            result["erpnext_docs"].extend(items_result.get('item_docs', []))
            
            # 3. Extract date and currency
            date_currency = self._extract_date_currency(extracted_doc, bill_no, document_score)
            document_score = date_currency.get('document_score', document_score)
            invoice_date = date_currency.get('invoice_date', '')
            currency = date_currency.get('currency', 'EUR')
            
            # 4. Extract payment terms
            payment_terms = extracted_doc.get("PaymentTerm", {}).get("valueString", "")
            
            # 5. Create Purchase Invoice structure
            purchase_invoice = {
                "doctype": "Purchase Invoice",
                "title": vendor_name,
                "supplier": vendor_name,
                "bill_no": bill_no,
                "bill_date": invoice_date,
                "posting_date": invoice_date,
                "currency": currency,
                "conversion_rate": 1,
                "set_posting_time": 1,
                "items": invoice_items,
                "payment_terms_template": payment_terms if frappe.db.exists("Payment Terms Template", payment_terms) else "",
            }
            
            # 6. Process amounts and adjust items if needed
            amounts_result = self._process_amounts(extracted_doc, invoice_items, bill_no)
            purchase_invoice["discount_amount"] = amounts_result.get('total_discount', 0)
            
            # Make sure to update the purchase_invoice with the final invoice_items list
            purchase_invoice["items"] = amounts_result.get('adjusted_items', invoice_items)

            # 7. Add taxes
            total_tax = amounts_result.get('total_tax', 0)
            if total_tax:
                vat_account = self._get_vat_account()
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

    # ======= Helper Methods for Both Auto and Manual Modes =======
            
    def _extract_invoice_details(self) -> Dict[str, Any]:
        """Extract basic invoice details from API response for manual mode"""
        try:
            response_data = json.loads(self.response)
            message = response_data.get("message", {})
            
            if not isinstance(message, dict) or not message.get("extracted_doc"):
                return {}
                
            extracted_doc = json.loads(message.get("extracted_doc"))
            
            # Extract bill number
            bill_no = extracted_doc.get("InvoiceId", {}).get("valueString", "")
            
            # Extract date
            invoice_date_str = extracted_doc.get("InvoiceDate", {}).get("valueDate", "")
            invoice_date = validate_and_fix_date(invoice_date_str, bill_no) if invoice_date_str else frappe.utils.today()
            
            # Extract currency
            currency = extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("currencyCode", "EUR")
            
            # Extract amount fields
            total_amount = self._round_amount(extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("amount", 0))
            total_tax = self._round_amount(extracted_doc.get("TotalTax", {}).get("valueCurrency", {}).get("amount", 0))
            
            # If no total amount found, try calculating from subtotal and tax
            if not total_amount:
                subtotal = self._round_amount(extracted_doc.get("SubTotal", {}).get("valueCurrency", {}).get("amount", 0))
                total_discount = self._round_amount(extracted_doc.get("TotalDiscount", {}).get("valueCurrency", {}).get("amount", 0))
                total_amount = subtotal + total_tax - total_discount
                
            return {
                'bill_no': bill_no,
                'invoice_date': invoice_date,
                'currency': currency,
                'total_amount': total_amount,
                'total_tax': total_tax
            }
        except Exception as e:
            frappe.log_error(f"Error extracting invoice details: {str(e)}")
            return {}
            
    def _extract_bill_number(self, extracted_doc, document_score):
        """Extract bill number from document"""
        bill_no = extracted_doc.get("InvoiceId", {}).get("valueString", "")
        if bill_no:
            document_score += 20
        return bill_no, document_score
            
    def _extract_vendor_info(self, extracted_doc, document_score):
        """Extract vendor information from document"""
        vendor_name = extracted_doc.get("VendorName", {}).get("valueString", "").replace("\n", " ").strip()
        if vendor_name:
            document_score += 20
            
        vendor_address = extracted_doc.get("VendorAddress", {}).get("valueAddress", {})
        vendor_tax_id = extracted_doc.get("VendorTaxId", {}).get("valueString", "")
        
        return {
            'vendor_name': vendor_name,
            'vendor_address': vendor_address,
            'vendor_tax_id': vendor_tax_id,
            'document_score': document_score
        }
        
    def _create_supplier_doc(self, vendor_info):
        """Create supplier document structure"""
        # Get supplier group from settings
        try:
            settings = frappe.get_doc("Invoice2Erpnext Settings")
            supplier_group = settings.supplier_group or "All Supplier Groups"
        except Exception as e:
            frappe.log_error(f"Error fetching settings: {str(e)}")
            supplier_group = "All Supplier Groups"  # Fallback to default
            
        vendor_name = vendor_info.get('vendor_name', '')
        vendor_address = vendor_info.get('vendor_address', {})
        vendor_tax_id = vendor_info.get('vendor_tax_id', '')
        
        return {
            "doctype": "Supplier",
            "supplier_name": vendor_name,
            "supplier_group": supplier_group,
            "supplier_type": "Company",  # Default value
            "country": vendor_address.get("countryRegion", "Cyprus"),
            "address_line1": vendor_address.get("streetAddress", ""),
            "city": vendor_address.get("city", "Larnaka"),
            "pincode": vendor_address.get("postalCode", ""),
            "tax_id": vendor_tax_id
        }
        
    def _extract_date_currency(self, extracted_doc, bill_no, document_score):
        """Extract date and currency information"""
        invoice_date = extracted_doc.get("InvoiceDate", {}).get("valueDate", "")
        invoice_date = validate_and_fix_date(invoice_date, bill_no)
        if invoice_date:
            document_score += 20
            
        currency = extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("currencyCode", "EUR")
        
        return {
            'invoice_date': invoice_date,
            'currency': currency,
            'document_score': document_score
        }
        
    def _process_items(self, extracted_doc, bill_no, document_score):
        """Process items from extracted document"""
        # Get settings
        try:
            settings = frappe.get_doc("Invoice2Erpnext Settings")
            one_item_invoice = settings.one_item_invoice or 0
            settings_item = settings.item if one_item_invoice else None
            item_group = settings.item_group or "All Item Groups"
        except Exception as e:
            frappe.log_error(f"Error fetching settings: {str(e)}")
            one_item_invoice = 0
            settings_item = None
            item_group = "All Item Groups"
            
        items = extracted_doc.get("Items", {}).get("valueArray", [])
        if items:
            document_score += 20
            
        invoice_items = []
        item_docs = []
        
        # Check for currency consistency among items
        invoice_currency = extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("currencyCode", "EUR")
        item_currencies = set()
        for item in items:
            item_currency = item.get("valueObject", {}).get("Amount", {}).get("valueCurrency", {}).get("currencyCode")
            if item_currency:
                item_currencies.add(item_currency)
        
        if item_currencies and any(curr != invoice_currency for curr in item_currencies):
            frappe.log_error(f"Currency mismatch: Invoice is {invoice_currency} but items have {item_currencies} in invoice {bill_no}")
        
        # Process items based on the one_item_invoice setting
        if one_item_invoice and settings_item and frappe.db.exists("Item", settings_item):
            # Single item mode
            result = self._process_single_item(items, settings_item, bill_no)
            invoice_items = result.get('invoice_items', [])
        else:
            # Multi-item mode
            result = self._process_multiple_items(items, item_group)
            invoice_items = result.get('invoice_items', [])
            item_docs = result.get('item_docs', [])
            
        return {
            'invoice_items': invoice_items,
            'item_docs': item_docs,
            'document_score': document_score
        }
        
    def _process_single_item(self, items, settings_item, bill_no):
        """Process all items as a single combined item"""
        # Calculate the total amount for all items
        total_amount = 0
        combined_description = []
        
        # Process each item to calculate totals but don't create separate items
        for idx, item in enumerate(items):
            item_data = item.get("valueObject", {})
            description = item_data.get("Description", {}).get("valueString", "")
            if description:
                combined_description.append(f"{idx+1}. {description}")
            
            amount = self._round_amount(item_data.get("Amount", {}).get("valueCurrency", {}).get("amount", 0))
            total_amount += amount
        
        # Create a single invoice item with quantity=1 and rate=total_amount
        invoice_item = {
            "item_code": settings_item,
            "qty": 1,  # Always use quantity of 1 for one_item_invoice
            "rate": total_amount,  # Rate equals total amount since qty=1
            "amount": total_amount,
            "description": "\n".join(combined_description) if combined_description else f"Combined invoice items for {bill_no}",
            "uom": "Nos"
        }
        
        return {
            'invoice_items': [invoice_item]
        }
        
    def _process_multiple_items(self, items, item_group):
        """Process multiple items individually"""
        invoice_items = []
        item_docs = []
        
        for idx, item in enumerate(items):
            item_data = item.get("valueObject", {})
            description = item_data.get("Description", {}).get("valueString", "")
            
            # Get product code if available, otherwise generate one
            product_code = item_data.get("ProductCode", {}).get("valueString", "")
            if product_code:
                item_code = f"{product_code}"
            else:
                # Generate item code based on description with hash for uniqueness
                import hashlib
                desc_hash = hashlib.md5(description.encode()).hexdigest()[:8] if description else ""
                item_code = f"I2E-{desc_hash}"
            
            # Get item details with standardized precision
            amount = self._round_amount(item_data.get("Amount", {}).get("valueCurrency", {}).get("amount", 0))
            unit_price = self._round_amount(item_data.get("UnitPrice", {}).get("valueCurrency", {}).get("amount", 0))
            quantity = item_data.get("Quantity", {}).get("valueNumber", 1) or 1  # Ensure quantity is never zero
            
            # Create Item document
            item_doc = {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": description.split("\n")[0][:140] if description else f"Item {idx+1}",
                "description": description,
                "item_group": item_group,
                "stock_uom": "Nos",
                "is_stock_item": 0,  # Assuming service item
                "is_purchase_item": 1
            }
            item_docs.append(item_doc)
            
            # Handle negative amounts (credits/refunds)
            is_credit = amount < 0
            
            # Create invoice item
            invoice_item = self._create_invoice_item(item_code, quantity, unit_price, amount, description, is_credit)
            invoice_items.append(invoice_item)
            
        return {
            'invoice_items': invoice_items,
            'item_docs': item_docs
        }
        
    def _create_invoice_item(self, item_code, quantity, unit_price, amount, description, is_credit):
        """Create an invoice item based on extracted data"""
        ROUNDING_TOLERANCE = 0.05
        
        if unit_price and quantity and amount:
            calculated_amount = self._round_amount(unit_price * quantity)
            
            # Handle both discount and markup scenarios
            if abs(calculated_amount - amount) > ROUNDING_TOLERANCE:
                # Use the final amount to determine the effective rate
                return {
                    "item_code": item_code,
                    "qty": abs(quantity),  # Always positive quantity
                    "rate": amount / quantity if quantity else amount,  # Add division by zero protection
                    "amount": amount,
                    "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                    "uom": "Nos"
                }
            else:
                # No discount/markup - use unit price as is
                return {
                    "item_code": item_code,
                    "qty": abs(quantity),  # Always positive quantity
                    "rate": unit_price * (-1 if is_credit else 1),
                    "amount": amount,
                    "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                    "uom": "Nos"
                }
        elif unit_price and quantity:
            # We have unit price and quantity but no amount
            calculated_amount = self._round_amount(unit_price * quantity)
            return {
                "item_code": item_code,
                "qty": abs(quantity),
                "rate": unit_price * (-1 if is_credit else 1),
                "amount": calculated_amount * (-1 if is_credit else 1),
                "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                "uom": "Nos"
            }
        elif amount:
            # We only have the amount
            return {
                "item_code": item_code,
                "qty": abs(quantity),
                "rate": amount / quantity if quantity else amount,  # Add division by zero protection
                "amount": amount,
                "description": f"CREDIT: {description}" if is_credit and not description.startswith("CREDIT:") else description,
                "uom": "Nos"
            }
        else:
            # Fallback if no pricing details at all
            return {
                "item_code": item_code,
                "qty": abs(quantity),
                "rate": 0,
                "amount": 0,
                "description": description,
                "uom": "Nos"
            }
        
    def _process_amounts(self, extracted_doc, invoice_items, bill_no):
        """Process and reconcile amount fields"""
        ROUNDING_TOLERANCE = 0.05
        
        # Extract amount fields with confidence scores
        subtotal = self._round_amount(extracted_doc.get("SubTotal", {}).get("valueCurrency", {}).get("amount", 0))
        subtotal_confidence = extracted_doc.get("SubTotal", {}).get("confidence", 0)

        invoice_total = self._round_amount(extracted_doc.get("InvoiceTotal", {}).get("valueCurrency", {}).get("amount", 0))
        invoice_total_confidence = extracted_doc.get("InvoiceTotal", {}).get("confidence", 0)

        total_tax = self._round_amount(extracted_doc.get("TotalTax", {}).get("valueCurrency", {}).get("amount", 0))
        total_tax_confidence = extracted_doc.get("TotalTax", {}).get("confidence", 0)

        total_discount = self._round_amount(extracted_doc.get("TotalDiscount", {}).get("valueCurrency", {}).get("amount", 0))
        total_discount_confidence = extracted_doc.get("TotalDiscount", {}).get("confidence", 0)

        # Calculate expected invoice total and validate against extracted total
        expected_total = self._round_amount(subtotal + total_tax - total_discount)
        
        # Reconcile inconsistencies in amount fields
        if invoice_total > 0:
            if abs(expected_total - invoice_total) > ROUNDING_TOLERANCE:
                # Find the field with lowest confidence
                confidences = {
                    "invoice_total": invoice_total_confidence,
                    "subtotal": subtotal_confidence,
                    "total_tax": total_tax_confidence,
                    "total_discount": total_discount_confidence
                }
                
                lowest_confidence_field = min(confidences, key=confidences.get)
                
                # Calculate the field with lowest confidence using other values
                if lowest_confidence_field == "invoice_total":
                    invoice_total = expected_total
                elif lowest_confidence_field == "subtotal":
                    subtotal = self._round_amount(invoice_total - total_tax + total_discount)
                elif lowest_confidence_field == "total_tax":
                    total_tax = self._round_amount(invoice_total - subtotal + total_discount)
                else:  # total_discount has lowest confidence
                    total_discount = self._round_amount(subtotal + total_tax - invoice_total)
        elif expected_total > 0:
            # If no invoice total was extracted but we can calculate it
            invoice_total = expected_total

        # Adjust item prices if needed
        calculated_line_total = self._round_amount(sum(item.get("qty", 0) * item.get("rate", 0) for item in invoice_items))
        adjusted_items = invoice_items.copy()
        
        if subtotal > 0 and abs(calculated_line_total - subtotal) > ROUNDING_TOLERANCE:
            adjusted_items = self._adjust_item_prices(invoice_items, subtotal, calculated_line_total, bill_no)
                
        return {
            'subtotal': subtotal,
            'invoice_total': invoice_total,
            'total_tax': total_tax,
            'total_discount': total_discount,
            'adjusted_items': adjusted_items
        }
        
    def _adjust_item_prices(self, invoice_items, subtotal, calculated_line_total, bill_no):
        """Adjust item prices to match the extracted subtotal"""
        ROUNDING_TOLERANCE = 0.05
        adjusted_items = invoice_items.copy()
        
        # Check if there's a huge disparity (likely decimal point issues)
        if calculated_line_total > subtotal * 10:
            # Simply divide by 100 for suspected decimal point issues
            for item in adjusted_items:
                item["rate"] = self._round_amount(item["rate"] / 100)
                item["amount"] = self._round_amount(item["qty"] * item["rate"])
            
            # Recalculate the total
            calculated_line_total = self._round_amount(sum(item.get("qty", 0) * item.get("rate", 0) for item in adjusted_items))
        
        # Apply proportional adjustment to any remaining discrepancy
        if abs(calculated_line_total - subtotal) > ROUNDING_TOLERANCE and calculated_line_total != 0:
            adjustment_factor = subtotal / calculated_line_total
            
            # Apply adjustment factor to ALL items' rates first
            for item in adjusted_items:
                original_rate = item.get("rate", 0)
                adjusted_rate = self._round_amount(original_rate * adjustment_factor)
                item["rate"] = adjusted_rate
                item["amount"] = self._round_amount(adjusted_rate * item.get("qty", 1))
            
            # Check if we still have a discrepancy after adjustment
            final_total = self._round_amount(sum(item.get("qty", 0) * item.get("rate", 0) for item in adjusted_items))
            if abs(final_total - subtotal) > 0:
                # Find the largest item to absorb the difference
                largest_item_idx = max(range(len(adjusted_items)), 
                                      key=lambda i: abs(adjusted_items[i].get("amount", 0)))
                
                # Adjust the amount directly for the largest item
                final_total_difference = subtotal - final_total
                largest_item = adjusted_items[largest_item_idx]
                largest_item["amount"] = self._round_amount(largest_item["amount"] + final_total_difference)
                
                # Recalculate rate based on the adjusted amount
                if largest_item.get("qty", 0):
                    largest_item["rate"] = self._round_amount(largest_item["amount"] / largest_item["qty"])
                
        return adjusted_items
    
    def _update_log_and_link_file(self, invoice_name):
        """Update the log document and link the file to the invoice"""
        self.created_docs = invoice_name
        
        # Modify the original file to link it to the Purchase Invoice
        if self.file:
            try:
                file_doc = frappe.get_doc("File", self.file)
                if file_doc:
                    # Update the file to be attached to the Purchase Invoice
                    file_doc.attached_to_doctype = "Purchase Invoice"
                    file_doc.attached_to_name = invoice_name
                    file_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error attaching file to Purchase Invoice: {str(e)}")
                
        # Update the status to "Completed"
        self.status = "Success"
        self.save()
    
    def _get_vat_account(self):
        """Get VAT account from settings"""
        try:
            settings = frappe.get_doc("Invoice2Erpnext Settings")
            vat_account = settings.vat_account or "VAT - TC"
            return vat_account
        except Exception as e:
            frappe.log_error(f"Error fetching Invoice2Erpnext Settings: {str(e)}")
            return "VAT - TC"  # Default fallback
    
    def _round_amount(self, amount):
        """Standardize decimal precision for monetary values"""
        if amount is None:
            return 0
        try:
            return round(float(amount), 2)
        except (ValueError, TypeError):
            return 0

@frappe.whitelist()
def create_purchase_invoice_from_file(file_doc_name, mode='auto', supplier=None, item=None):
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
                
                # For manual mode, store the supplier and item selection
                if mode == 'manual' and supplier and item:
                    doc.message = "Manual selection mode - using specified supplier and item"
                    doc.manual_mode = 1  # Flag to indicate manual processing
                    doc.manual_supplier = supplier
                    doc.manual_item = item
                else:
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

def validate_and_fix_date(date_string, reference_id=""):
    """
    Validates and fixes a date string to YYYY-MM-DD format.
    If validation fails, returns today's date.
    
    Args:
        date_string: The date string to validate/fix
        reference_id: Optional reference ID for logging (e.g., invoice number)
        
    Returns:
        string: YYYY-MM-DD formatted date
    """
    if not date_string:
        frappe.log_error(f"Date missing in document {reference_id}, using today's date")
        return frappe.utils.today()
    
    # Check if it's already in expected YYYY-MM-DD format
    if len(date_string.split('-')) == 3:
        try:
            # Verify it's actually a valid date
            from datetime import datetime
            datetime.strptime(date_string, '%Y-%m-%d')
            return date_string
        except ValueError:
            pass  # Fall through to the parsing logic below
    
    # Try to parse and fix common date formats
    try:
        from datetime import datetime
        
        # Try different date formats (day/month/year, month/day/year, etc.)
        possible_formats = [
            '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d',
            '%d-%m-%Y', '%m-%d-%Y', '%Y-%m-%d',
            '%d.%m.%Y', '%m.%d.%Y', '%Y.%m.%d',
            '%d %b %Y', '%b %d %Y', '%d %B %Y', '%B %d %Y'
        ]
        
        parsed_date = None
        for date_format in possible_formats:
            try:
                parsed_date = datetime.strptime(date_string, date_format)
                break
            except ValueError:
                continue
        
        if parsed_date:
            # Convert to YYYY-MM-DD format
            fixed_date = parsed_date.strftime('%Y-%m-%d')
            frappe.log_error(f"Fixed invalid date format in document {reference_id}: {date_string} → {fixed_date}")
            return fixed_date
        else:
            # If we couldn't parse the date, use today's date as fallback
            frappe.log_error(f"Couldn't parse date in document {reference_id}: {date_string}, using today's date instead")
            return frappe.utils.today()
    except Exception as e:
        frappe.log_error(f"Error processing date in document {reference_id}: {str(e)}, using today's date")
        return frappe.utils.today()
