import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_outstanding_reference_documents
from datetime import datetime, timedelta

@frappe.whitelist()
def fetch_outstanding_invoices_custom(posting_date, company, party_type, payment_type, party, party_account):
    try:
        # Convert string to date object
        posting_date_obj = datetime.strptime(posting_date, "%Y-%m-%d")
        to_posting_date = posting_date_obj.strftime("%Y-%m-%d")
        
        args = {
            "posting_date": posting_date,
            "company": company,
            "party_type": party_type,
            "payment_type": payment_type,
            "party": party,
            "party_account": party_account,
            "from_posting_date": "1900-01-01",
            "to_posting_date": to_posting_date,
            "outstanding_amt_greater_than": 0,
            "allocate_payment_amount": 1,
            "get_outstanding_invoices": True
        }
        
        return get_outstanding_reference_documents(args=args)
    
    except Exception as e:
        frappe.log_error("Error in fetch_outstanding_invoices_custom", str(e))