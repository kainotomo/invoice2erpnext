# Invoice2Erpnext

A seamless integration for automatically processing invoices and creating Purchase Invoices in ERPNext.

## Overview

Invoice2Erpnext is an advanced tool that automatically processes invoices from various formats (PDF, images, etc.) and creates Purchase Invoices in ERPNext. The system extracts data from invoice documents, intelligently reconciles financial information, and creates all necessary related documents.

## Prerequisites

Before using Invoice2Erpnext, ensure:

1. You've installed the Invoice2Erpnext app in your ERPNext instance
2. Your administrator has configured the "Invoice2Erpnext Settings" with:
   - API credentials (api_key and api_secret)
   - BASE_URL for the document extraction service
   - Default VAT account

## How to Use

### Processing Invoices

To process invoices with Invoice2Erpnext:

1. Navigate to the **Purchase Invoice** list view
2. Click the "Upload" button in the list view
3. Select the invoice files you want to process
4. The system will:
   - Process each file automatically
   - Create Purchase Invoices in draft status
   - Generate Logs with the result

Once processed, you can review and submit the created Purchase Invoices after verifying their accuracy.

## Understanding the Process

The system performs these steps automatically:

1. **Document Extraction**: Sends the invoice to an AI service that reads text and structures
2. **Data Validation**: Checks for consistency in extracted financial data
3. **Intelligent Reconciliation**: If discrepancies exist, determines which values are most reliable based on confidence scores
4. **Document Creation**:
   - Creates Supplier if not already in system
   - Creates Items if not already in system
   - Creates Purchase Invoice with line items, taxes, and totals
5. **File Attachment**: Links the original invoice file to the created Purchase Invoice

## Monitoring Results

After processing, use the Invoice2Erpnext Log to monitor status:

1. Navigate to **Invoice2Erpnext Log** in your ERPNext menu
2. View processing status for each uploaded file:
   - Status: Shows "Success" if completed successfully
   - Created Docs: Lists all documents created from the invoice
   - Message: Contains detailed processing information

The original file will be automatically attached to the new Purchase Invoice.

## Troubleshooting

If processing fails:
- Check the Invoice2Erpnext Log status and message fields
- Common issues include:
  - Poor quality scans of invoices
  - Missing critical data (vendor name, invoice date, etc.)
  - Inconsistent totals that can't be reconciled
  - Connection issues with the extraction service

For best results, ensure your invoice files are clear, properly scanned, and contain all critical information.