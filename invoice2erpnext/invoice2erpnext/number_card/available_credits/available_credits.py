import frappe

@frappe.whitelist()
def get_credits():
    """Get available credits from Invoice2Erpnext Settings"""
    try:
        # Use the correct DocType name
        settings = frappe.get_doc("Invoice2Erpnext Settings")
        
        # Get credits value or 0 if not set
        credits_value = settings.get_credits() if hasattr(settings, "credits") else 0
        
        # Return formatted response
        return {
            "value": credits_value,
            "fieldtype": "Currency",
        }
    except Exception as e:
        frappe.log_error(f"Error fetching credits: {str(e)}", "Invoice2Erpnext Credits")
        return {
            "value": 0,
            "fieldtype": "Currency",
        }