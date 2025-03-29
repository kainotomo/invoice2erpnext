# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe

def format_currency_value(value):
    """
    Helper function to format currency values according to system settings
    
    Args:
        value: The value to format (string or numeric)
        
    Returns:
        str: Formatted value according to system number format
    """
    # First ensure we have a float value to work with
    if isinstance(value, str):
        # Handle if value is in string format with comma or period
        value_float = float(value.replace(',', '.'))
    else:
        value_float = float(value)
    
    # Get the number format from system settings
    number_format = frappe.get_system_settings('number_format')
    
    # Format according to the system's number format
    if number_format == "#.###,##":  # European format (1.234,56)
        formatted_value = str(value_float).replace(".", ",")
    elif number_format == "# ###.##":  # Format with space (1 234.56)
        integer_part, decimal_part = str(value_float).split(".")
        formatted_value = " ".join([integer_part, decimal_part])
    elif number_format == "#,###.##":  # US format (1,234.56)
        formatted_value = str(value_float)
    else:
        # Default format if none of the above
        formatted_value = str(value_float)
    
    return formatted_value