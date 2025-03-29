# Copyright (c) 2025, KAINOTOMO PH LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests

class Invoice2ErpnextSettings(Document):
	"""Settings for Invoice2ERPNext integration"""
		
	@frappe.whitelist()
	def get_credits(self):
		"""Test connection to ERPNext API and fetch user credits"""
		
		# Check if integration is enabled
		if hasattr(self, 'enabled') and self.enabled == 0:
			return {
				"success": False,
				"message": "Integration is disabled. Please enable it in settings."
			}
		
		# Base URL is defined as a constant
		BASE_URL = "http://development.localhost:8001/"
		
		try:
			api_key = self.get_password('api_key')
			api_secret = self.get_password('api_secret') if hasattr(self, 'get_password') else self.api_secret
			
			# Prepare API request headers with decrypted credentials
			headers = {
				"Authorization": f"token {api_key}:{api_secret}",
				"Content-Type": "application/json"
			}
			
			# Make request to the get_user_credits endpoint
			endpoint = f"{BASE_URL}/api/method/doc2sys.doc2sys.doctype.doc2sys_user_settings.doc2sys_user_settings.get_user_credits"
			
			# You might need to pass specific user information if required
			data = {}
			if hasattr(self, 'erpnext_user') and self.erpnext_user:
				data = {"user": self.erpnext_user}
			
			# Make the API request
			response = requests.post(
				endpoint,
				headers=headers,
				json=data
			)
			
			# Process the response
			if response.status_code == 200:
				result = response.json()
				
				# If API call was successful
				if result.get("message") and result["message"].get("success"):
					# Extract credits from response
					credits = result["message"].get("credits", 0)
					
					return {
						"success": True,
						"credits": credits,
						"message": "Successfully connected to ERPNext API"
					}
				else:
					error_msg = result.get("message", {}).get("message", "API returned error")
					return {
						"success": False,
						"message": f"API Error: {error_msg}"
					}
			else:
				# Handle HTTP errors
				return {
					"success": False,
					"message": f"HTTP Error: {response.status_code} - {response.text}"
				}
				
		except Exception as e:
			frappe.log_error(f"ERPNext API Connection Error: {str(e)}", "Invoice2ERPNext")
			return {
				"success": False,
				"message": f"Connection Error: {str(e)}"
			}

	@frappe.whitelist()
	def test_connection(self):
		"""Test the connection to the ERPNext API"""
		self.enabled = 1
		result = self.get_credits()
		if result.get("success"):
			self.enabled = 1
		else:
			self.enabled = 0
		
		self.save()

		return result