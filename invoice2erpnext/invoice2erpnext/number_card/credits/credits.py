import frappe

def get_credits():
    """Get available credits from Invoice2Erpnext Settings"""
    try:
        # Use the correct DocType name
        settings = frappe.get_doc("Invoice2ErpnextSettings")
        
        # Return credits or 0 if not set
        return settings.credits if hasattr(settings, "credits") else 0
    except Exception as e:
        frappe.log_error(f"Error fetching credits: {str(e)}", "Invoice2Erpnext Credits")
        return 0