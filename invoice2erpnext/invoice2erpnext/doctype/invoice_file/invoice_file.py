# Copyright (c) 2023, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
import os
import json
from json2table import convert
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
import datetime

class InvoiceFile(Document):

	def on_update(self):
		update_invoice_file_result(self)
			
def update_invoice_file_result(doc):
	if doc.file:
		folder_path = os.path.join(frappe.local.site_path, "invoice_template")
		templates = read_templates(folder_path)
		file = frappe.get_doc("File", {"file_url": doc.file})
		file_path = file.get_full_path()
		result = extract_data(file_path, templates=templates)
		if result:
			doc.result = json.dumps(result, indent=4, default=lambda x: x.isoformat() if isinstance(x, datetime.datetime) else None)
			doc.html_table = convert(result)
			frappe.db.set_value('Invoice File', doc.name, {
				'result': doc.result,
				'html_table': doc.html_table
			})
	else:
		frappe.db.set_value('Invoice File', doc.name, {
				'result': None,
				'html_table': None
			})
			
def comma_to_dot(number_str):
	if isinstance(number_str, str):
		number_str = float(number_str.replace(",", "."))
	return number_str

@frappe.whitelist()
def make_purchase_invoice(source_name, doc_type):
	invoice_file_doc = frappe.get_doc("Invoice File", source_name)
	result = json.loads(invoice_file_doc.result)

	pi = frappe.new_doc(doc_type)
	pi.supplier = result["issuer"]
	pi.currency = result.get('currency', None)
	pi.conversion_rate = comma_to_dot(result.get('conversion_rate', 1))
	pi.is_return = result.get('is_return', None)
	pi.return_against = result.get('return_against', None)
	pi.is_subcontracted = result.get('is_subcontracted', 0)
	pi.supplier_warehouse = result.get('supplier_warehouse', None)
	pi.cost_center = result.get('cost_center', None)
	
	pi.set_posting_time = 1
	pi.posting_date = result.get('date', frappe.utils.today())
	pi.transaction_date = pi.posting_date
	pi.schedule_date = pi.posting_date
	pi.due_date = pi.posting_date
	pi.bill_no = result.get('invoice_number', None)
	pi.bill_date = result.get('bill_date', pi.posting_date)

	pi.append(
		"items",
		{
			"item_code": result['item_code'],
			"uom": result.get('uom', None),
			"warehouse": result.get('warehouse', None),
			"qty": result.get('qty', 1),
			"received_qty":comma_to_dot(result.get('received_qty', 0)),
			"rejected_qty": comma_to_dot(result.get('rejected_qty', 0)),
			"rate": comma_to_dot(result.get('amount', 0)),
			"price_list_rate": result.get('price_list_rate', None),
			"expense_account": result.get('expense_account', None),
			"discount_account": result.get('discount_account', None),
			"discount_amount": comma_to_dot(result.get('discount_amount', 0)),
			"conversion_factor": 1.0,
			"serial_no": result.get('serial_no', None),
			"stock_uom": result.get('stock_uom', None),
			"cost_center": result.get('cost_center', None),
			"project": result.get('project', None),
			"rejected_warehouse": result.get('rejected_warehouse', None),
			"rejected_serial_no": result.get('rejected_serial_no', None),
			"asset_location": result.get('asset_location', None),
			"allow_zero_valuation_rate": comma_to_dot(result.get('allow_zero_valuation_rate', 0)),
			"schedule_date": pi.posting_date
		},
	)

	if result.get('tax_account_head'):
		pi.append("taxes", {
			"account_head": result['tax_account_head'],
			"add_deduct_tax": "Add",
			"category": "Total",
			"charge_type": "Actual",
			"cost_center": result.get('tax_cost_center', None),
			"description": result.get('tax_description', "TAX"),
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "taxes",
			"rate": 0,
			"tax_amount": comma_to_dot(result.get('tax_amount', 0))
		})
	
	pi.save();
	frappe.db.set_value('Invoice File', source_name, {'status': 'Purchase Invoice created'})

	return pi.name

def set_file_from_communication(doc, method):
	if doc.attached_to_doctype == "Communication":
		communication = frappe.get_doc("Communication", doc.attached_to_name)
		if communication.reference_doctype == "Invoice File":
			invoice_file = frappe.get_doc("Invoice File", communication.reference_name)
			if invoice_file:
				invoice_file.file = doc.file_url
				frappe.db.set_value('Invoice File', invoice_file.name, {
					'file': doc.file_url,
				})
				update_invoice_file_result(invoice_file)
				make_purchase_invoice(invoice_file.name, "Purchase Invoice")