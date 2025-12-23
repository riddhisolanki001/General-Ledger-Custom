
import frappe
@frappe.whitelist()
def get_general_ledger_prepared_data():
    """
    Returns parsed data + applied filter values from the latest
    Prepared Report for General Ledger.
    Detects gzip and plain JSON storage.
    Works on ERPNext v12/v13/v14 environments.
    """
    import json
    import gzip
    from frappe.utils.file_manager import get_file_path

    # Step 1: Get latest Prepared Report
    pr = frappe.get_all(
        "Prepared Report",
        filters={"report_name": "General Ledger"},
        fields=["name", "filters"],  # ← include filters field
        order_by="creation desc",
        limit=1
    )

    if not pr:
        return {"success": False, "message": "No Prepared Report found for General Ledger"}

    pr = pr[0]
    prepared_report_name = pr.name

    # Parse filters JSON (may be empty)
    applied_filters = frappe.parse_json(pr.filters) if pr.filters else {}

    # Step 2: Get latest attached output file
    file_doc = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Prepared Report",
            "attached_to_name": prepared_report_name
        },
        fields=["file_url"],
        order_by="creation desc",
        limit=1
    )

    if not file_doc:
        return {"success": False, "message": "No report file found (maybe still generating?)"}

    file_path = get_file_path(file_doc[0].file_url)

    # Step 3: Load JSON content (gzip aware)
    try:
        with gzip.open(file_path, "rb") as gz:
            raw = gz.read().decode("utf-8")
        content = json.loads(raw)
    except OSError:
        with open(file_path, "r") as f:
            content = json.load(f)

    data = content.get("result", []) or content.get("data", [])

    # Safely extract required boundary values
    first_row = data[0] if len(data) > 0 else None
    last_row = data[-1] if len(data) > 0 else None
    second_last_row = data[-2] if len(data) > 1 else None
    
    cleaned_data = data.copy()  
    if len(cleaned_data) > 0:
        cleaned_data.pop(0)  
    if len(cleaned_data) > 0:
        cleaned_data.pop(-1)  
    if len(cleaned_data) > 1:
        cleaned_data.pop(-1) 

    return {
        "success": True,
        "prepared_report": prepared_report_name,
        "applied_filters": applied_filters,
        "data": cleaned_data,
        "balance_details": {
            "opening": first_row,
            "total": second_last_row,
            "closing": last_row
        }
    }
