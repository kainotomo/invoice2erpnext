## Invoice2Erpnext
Data extractor for PDF invoices

This applicate is using on https://github.com/invoice-x/invoice2data to extract the data from PDF files.
Then it uses the data to import invoices to ErpNext

#### License
MIT
### Installation
* Update apt with command: `sudo apt update`

* install pdftotext on Ubuntu, you can use the following command in the terminal:
`sudo apt install poppler-utils`
This will install the poppler-utils package which includes pdftotext

* Install invoice2data using pip
`bench pip install invoice2data`

* Install json to table using pip
`bench pip install json2table`

#### Installation of input modules
An tesseract wrapper is included in auto language mode. It will test your input files against the languages installed on your system. To use it tesseract and imagemagick needs to be installed. tesseract supports multiple OCR engine modes. By default the available engine installed on the system will be used.

Languages: tesseract-ocr recognize more than 100 languages For Linux users, you can often find packages that provide language packs:

**Display a list of all Tesseract language packs**
`sudo apt-cache search tesseract-ocr`

**Debian/Ubuntu users**
`sudo apt-get install tesseract-ocr-ell`  # Example: Install Greek language pack

**Arch Linux users**
`pacman -S tesseract-data-eng tesseract-data-deu` # Example: Install the English and German language packs

### How to use
After installing access the app to the created workspace called Invoice2Erpnext. There are two doctypes.
* **Invoice Template** - add/modify templates
* **Invoice File** - upload and create Purchase Invoices

Each purchase invoice is created with one item.

### Template system
Read Invoice2Data template system documentation on how to use it. https://github.com/invoice-x/invoice2data#template-system 

In addition the integration with erpnext is as below.

#### Required fields
* issuer - the supplier. Must already exist in the system
* date - the posting date invoice was issued
* invoice_number - unique number assigned to invoice by an issuer
* item_code - The item code in erpnext
* amount - The item rate
#### Additional fields
Note that if erpnext have default values, then None will default to that value.
**General fields of the invoice**
* currency - Defaults to None
* conversion_rate - Defaults to 1
* is_return - Defaults to None
* return_against - Defaults to None
* is_subcontracted - Defaults to 0
* supplier_warehouse - Defaults to None
* cost_center - Defaults to None
* due_date - Defaults to posting_date
* bill_date - Defaults to posting_Date
**Item specific fields**
* warehouse - Defaults to None
* qty - Defaults to 1
* received_qty - Defaults to 0
* rejected_qty - Defaults to 0
* price_list_rate - Defaults to None
* expense_account - Defaults to None
* discount_account - Defaults to None
* discount_amount - Defaults to None
* conversion_factor - Defaults to 1
* serial_no - Defaults to None
* stock_uom - Defaults to None
* cost_center - Defaults to None
* project - Defaults to None
* rejected_warehouse - Defaults to None
* rejected_serial_no - Defaults to None
* asset_location - Defaults to None
* allow_zero_valuation_rate - Defaults to 0
**Tax**
* tax_account_head - Tax account (required)
* tax_cost_center - Defaults to None
* tax_description - Defaults to "TAX"
* tax_amount - Defaults to 0
