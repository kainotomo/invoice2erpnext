# Copyright (c) 2023, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os


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
        # open the file in write mode
        with open(file_path, "w") as f:
            # write the yml text to the file
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
