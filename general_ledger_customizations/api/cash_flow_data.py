import frappe
import json
import gzip
from frappe.utils.file_manager import get_file_path

@frappe.whitelist()
def get_cash_flow_prepared_data():
    
    try:
        """
        Returns parsed data + applied filter values from the latest
        Prepared Report for Trial Balance.
        Detects gzip and plain JSON storage.
        """
        
        # Step 1: Get latest Prepared Report for Trial Balance
        pr = frappe.get_all(
            "Prepared Report",
            filters={"report_name": "Cash Flow"},
            fields=["name", "filters"],
            order_by="creation desc",
            limit=1
        )

        if not pr:
            return {
                "success": False, 
                "message": "No Prepared Report found for Trial Balance. Please generate the report first."
            }

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
            return {
                "success": False, 
                "message": "No report file found (maybe still generating?)"
            }

        file_path = get_file_path(file_doc[0].file_url)

        # Step 3: Load JSON content (gzip aware)
        try:
            with gzip.open(file_path, "rb") as gz:
                raw = gz.read().decode("utf-8")
            content = json.loads(raw)
        except OSError:
            with open(file_path, "r") as f:
                content = json.load(f)

        # Extract columns and data
        columns = content.get("columns", [])
        data = content.get("result", []) or content.get("data", [])

        # Filter out hidden columns
        visible_columns = [col for col in columns if not col.get('hidden', False)]

        return {
            "success": True,
            "prepared_report": prepared_report_name,
            "applied_filters": applied_filters,
            "columns": visible_columns,
            "data": data
        }
    
    except Exception as e:
        frappe.log_error("get_cash_flow_prepared_data", frappe.get_traceback())
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }