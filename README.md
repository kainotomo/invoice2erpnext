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

#### Installation of input modules
An tesseract wrapper is included in auto language mode. It will test your input files against the languages installed on your system. To use it tesseract and imagemagick needs to be installed. tesseract supports multiple OCR engine modes. By default the available engine installed on the system will be used.

Languages: tesseract-ocr recognize more than 100 languages For Linux users, you can often find packages that provide language packs:

# Display a list of all Tesseract language packs
`sudo apt-cache search tesseract-ocr

# Debian/Ubuntu users
sudo apt-get install tesseract-ocr-ell  # Example: Install Greek language pack

# Arch Linux users
pacman -S tesseract-data-eng tesseract-data-deu # Example: Install the English and German language packs
`