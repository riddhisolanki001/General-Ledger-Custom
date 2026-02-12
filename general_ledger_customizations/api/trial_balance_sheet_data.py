from erpnext.accounts.report.trial_balance.trial_balance import execute
import frappe
@frappe.whitelist()
def get_trial_balance_data(filters=None):
    filters = frappe._dict(filters or {})
    
    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year is required")

    columns, data = execute(filters)

    return {
        "success": True,
        "columns": columns,
        "data": data,
        "filters": filters
    }
