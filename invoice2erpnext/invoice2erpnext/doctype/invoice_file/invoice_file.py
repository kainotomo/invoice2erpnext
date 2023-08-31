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
