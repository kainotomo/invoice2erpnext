# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe

def format_currency_value(value):
    """
    Helper function to format currency values according to system settings
    
    Args:
        value: The value to format (string or numeric)
        
    Returns:
        str: Formatted value according to system number format and currency precision
    """
    # First ensure we have a float value to work with
    if isinstance(value, str):
        # Handle if value is in string format with comma or period
        value_float = float(value.replace(',', '.'))
    else:
        value_float = float(value)
    
    # Get currency precision from Frappe
    try:
        currency_precision = frappe.get_precision("Currency", "amount")
        if currency_precision is None:
            currency_precision = 2  # Default to 2 decimal places
    except:
        currency_precision = 2  # Default to 2 decimal places if anything goes wrong
    
    # Round the value to the specified precision
    value_float = round(value_float, currency_precision)
    
    # Format with the exact number of decimal places
    value_str = f"{{:.{currency_precision}f}}".format(value_float)
    
    # Get the number format from system settings
    number_format = frappe.get_system_settings('number_format')
    
    # Format according to the system's number format
    if number_format == "#.###,##":  # European format (1.234,56)
        formatted_value = value_str.replace(".", ",")
    elif number_format == "# ###.##":  # Format with space (1 234.56)
        integer_part, decimal_part = value_str.split(".")
        formatted_value = f"{integer_part} {decimal_part}"
    elif number_format == "#,###.##":  # US format (1,234.56)
        formatted_value = value_str
    else:
        # Default format if none of the above
        formatted_value = value_str
    
    return formatted_value

@frappe.whitelist()
def check_settings_enabled():
    """Safely check if Invoice2Erpnext is enabled without permission errors"""
    # First check if user has permission to read the settings
    if not frappe.has_permission("Invoice2Erpnext Settings", "read"):
        return 0
    
    try:
        return frappe.db.get_single_value('Invoice2Erpnext Settings', 'enabled')
    except:
        # Return 0 (disabled) if any error occurs
        return 0