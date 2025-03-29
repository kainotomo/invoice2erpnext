# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Invoice2ErpnextSettings(Document):
	pass

#def set_file_from_communication(doc, method):
#	if doc.attached_to_doctype == "Communication":
#		communication = frappe.get_doc("Communication", doc.attached_to_name)
#		if communication.reference_doctype == "Invoice File":
#			invoice_file = frappe.get_doc("Invoice File", communication.reference_name)
#			if invoice_file:
#				invoice_file.file = doc.file_url
#				frappe.db.set_value('Invoice File', invoice_file.name, {
#					'file': doc.file_url,
#				})
#				update_invoice_file_result(invoice_file)
#				make_purchase_invoice(invoice_file.name, "Purchase Invoice")
