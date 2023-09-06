# Copyright (c) 2023, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
import yaml
import json

class InvoiceTemplate(Document):
    # define a function to write yml text to a file
    def write_yml_to_file(doc):
        # get the yml field value
        yml_text = doc.yml
        # create a file name with the document name
        file_name = doc.name + ".yml"
        # create a folder path under the site
        folder_path = os.path.join(frappe.local.site_path, "invoice_template")
        # create the folder if it does not exist
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        # create a file path with the folder and file name
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, 'w') as f:
            f.write(yml_text)

    # define a function to delete yml file
    def delete_yml_file(doc):
        # create a file name with the document name
        file_name = doc.name + ".yml"
        # create a folder path under the site
        folder_path = os.path.join(frappe.local.site_path, "invoice_template")
        # create a file path with the folder and file name
        file_path = os.path.join(folder_path, file_name)
        # remove the file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)

    # define a function to rename yml file
    def rename_yml_file(doc, old_name):
        # create an old file name with the old document name
        old_file_name = old_name + ".yml"
        # create a new file name with the new document name
        new_file_name = doc.name + ".yml"
        # create a folder path under the site
        folder_path = os.path.join(frappe.local.site_path, "invoice_template")
        # create an old file path with the folder and old file name
        old_file_path = os.path.join(folder_path, old_file_name)
        # create a new file path with the folder and new file name
        new_file_path = os.path.join(folder_path, new_file_name)
        # rename the file if it exists
        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)

    # override the on_update method of the Document class
    def on_update(self):
        self.write_yml_to_file()

    # override the on_trash method of the Document class
    def on_trash(self):
        self.delete_yml_file()

    # override the after_rename method of the Document class
    def after_rename(self, old_name, new_name, merge=False):
        self.rename_yml_file(old_name)

@frappe.whitelist()
def generate_yml(doc):
    invoice_template = json.loads(doc)
    result = {}
    result['issuer'] = invoice_template['issuer']
    
    fields = {}
    fields['amount'] = invoice_template['amount']
    fields['date'] = invoice_template['date']
    fields['invoice_number'] = invoice_template['invoice_number']
    fields['item_code'] = {
        'parser': 'static',
        'value': invoice_template['item_code']
        }
    if 'tax_account_head' in invoice_template:
        fields['tax_account_head'] = {
            'parser': 'static',
            'value': invoice_template['tax_account_head']
        }
        fields['tax_amount'] = invoice_template['tax_amount']
    if 'expense_account' in invoice_template:
        fields['expense_account'] = {
            'parser': 'static',
            'value': invoice_template['expense_account']
        }
    result['fields'] = fields

    options = {}
    options['currency'] = invoice_template['currency']
    options['remove_whitespace'] = invoice_template['remove_whitespace']
    options['date_formats'] = [invoice_template['date_formats']]
    options['decimal_separator'] = invoice_template['decimal_separator']
    result['options'] = options

    keywords = []
    for keyword in invoice_template['keywords']:
        keywords.append(keyword['keyword'])
    result['keywords'] = keywords

    return yaml.dump(result)