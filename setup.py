from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in invoice2erpnext/__init__.py
from invoice2erpnext import __version__ as version

setup(
	name="invoice2erpnext",
	version=version,
	description="Data extractor for PDF invoices",
	author="KAINOTOMO PH LTD",
	author_email="info@kainotomo.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
