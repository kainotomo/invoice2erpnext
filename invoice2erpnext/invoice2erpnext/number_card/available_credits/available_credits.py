import frappe

@frappe.whitelist()
def get_credits():
    """Get available credits from Invoice2Erpnext Settings"""
    try:
        # Use the correct DocType name
        settings = frappe.get_doc("Invoice2Erpnext Settings")
        
        # Get credits value or 0 if not set
        result = settings.get_credits()
        
        # Extract credits from result if successful
        credits = 0
        if result.get("success") and "credits" in result:
            credits = result["credits"]
        
        # Return formatted response
        return {
            "value": credits,
            "fieldtype": "Currency",
        }
    except Exception as e:
        frappe.log_error(f"Error fetching credits: {str(e)}", "Invoice2Erpnext Credits")
        return {
            "value": 0,
            "fieldtype": "Currency",
        }