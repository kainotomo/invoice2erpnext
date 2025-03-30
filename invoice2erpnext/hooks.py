from . import __version__ as app_version

app_name = "invoice2erpnext"
app_title = "Invoice2Erpnext"
app_publisher = "KAINOTOMO PH LTD"
app_description = "Data extractor for PDF invoices"
app_email = "info@kainotomo.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/invoice2erpnext/css/invoice2erpnext.css"
# app_include_js = "/assets/invoice2erpnext/js/invoice2erpnext.js"

# include js, css files in header of web template
# web_include_css = "/assets/invoice2erpnext/css/invoice2erpnext.css"
# web_include_js = "/assets/invoice2erpnext/js/invoice2erpnext.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "invoice2erpnext/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_list_js = {"Purchase Invoice" : "public/js/purchase_invoice_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "invoice2erpnext.utils.jinja_methods",
#	"filters": "invoice2erpnext.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "invoice2erpnext.install.before_install"
# after_install = "invoice2erpnext.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "invoice2erpnext.uninstall.before_uninstall"
# after_uninstall = "invoice2erpnext.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "invoice2erpnext.utils.before_app_install"
# after_app_install = "invoice2erpnext.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "invoice2erpnext.utils.before_app_uninstall"
# after_app_uninstall = "invoice2erpnext.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "invoice2erpnext.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

#doc_events = {
#    "File": {
#		"after_insert": "invoice2erpnext.invoice2erpnext.doctype.invoice2erpnext.invoice2erpnext.set_file_from_communication"
#	}
#}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"invoice2erpnext.tasks.all"
#	],
#	"daily": [
#		"invoice2erpnext.tasks.daily"
#	],
#	"hourly": [
#		"invoice2erpnext.tasks.hourly"
#	],
#	"weekly": [
#		"invoice2erpnext.tasks.weekly"
#	],
#	"monthly": [
#		"invoice2erpnext.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "invoice2erpnext.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "invoice2erpnext.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "invoice2erpnext.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["invoice2erpnext.utils.before_request"]
# after_request = ["invoice2erpnext.utils.after_request"]

# Job Events
# ----------
# before_job = ["invoice2erpnext.utils.before_job"]
# after_job = ["invoice2erpnext.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"invoice2erpnext.auth.validate"
# ]
