# Copyright (c) 2023, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
import os
import json
from json2table import convert
import datetime
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class InvoiceFile(Document):

	def on_update(self):
		folder_path = os.path.join(frappe.local.site_path, "invoice_template")
		templates = read_templates(folder_path)
		if self.file:
			file = frappe.get_doc("File", {"file_url": self.file})
			file_path = file.get_full_path()
			result = extract_data(file_path, templates=templates)
			if result:
				self.result = json.dumps(result, indent=4, default=lambda x: x.isoformat() if isinstance(x, datetime.datetime) else None)
				self.html_table = convert(result)
				frappe.db.set_value('Invoice File', self.name, {
					'result': self.result,
					'html_table': self.html_table
				})
		else:
			frappe.db.set_value('Invoice File', self.name, {
					'result': None,
					'html_table': None
				})
			
@frappe.whitelist()
def make_purchase_invoice(source_name):
	invoice_file_doc = frappe.get_doc("Invoice File", source_name)
	result = json.loads(invoice_file_doc.result)

	pi = frappe.new_doc("Purchase Invoice")
	pi.supplier = result["issuer"]
	pi.currency = result.get('currency', None)
	pi.conversion_rate = result.get('conversion_rate', 1)
	pi.is_return = result.get('is_return', None)
	pi.return_against = result.get('return_against', None)
	pi.is_subcontracted = result.get('is_subcontracted', 0)
	pi.supplier_warehouse = result.get('supplier_warehouse', None)
	pi.cost_center = result.get('cost_center', None)
	
	pi.posting_date = result.get('date', frappe.utils.today())
	pi.due_date = result.get('date', None)
	pi.bill_no = result.get('invoice_number', None)
	pi.bill_date = result.get('bill_date', pi.posting_date)

	pi.append(
		"items",
		{
			"item_code": result['item_code'],
			"warehouse": result.get('warehouse', None),
			"qty": result.get('qty', 1),
			"received_qty":result.get('received_qty', 0),
			"rejected_qty": result.get('rejected_qty', 0),
			"rate": result.get('amount', 0),
			"price_list_rate": result.get('price_list_rate', 50),
			"expense_account": result.get('expense_account', None),
			"discount_account": result.get('discount_account', None),
			"discount_amount": result.get('discount_amount', 0),
			"conversion_factor": 1.0,
			"serial_no": result.get('serial_no', None),
			"stock_uom": result.get('stock_uom', None),
			"cost_center": result.get('cost_center', None),
			"project": result.get('project', None),
			"rejected_warehouse": result.get('rejected_warehouse', None),
			"rejected_serial_no": result.get('rejected_serial_no', None),
			"asset_location": result.get('asset_location', None),
			"allow_zero_valuation_rate": result.get('allow_zero_valuation_rate', 0),
		},
	)
	
	pi.save();
	frappe.db.set_value('Invoice File', source_name, {'status': 'Purchase Invoice created'})

	return pi.name


