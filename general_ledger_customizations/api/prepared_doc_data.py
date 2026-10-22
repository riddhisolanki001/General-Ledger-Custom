import frappe, re
from frappe import _


@frappe.whitelist()
def get_general_ledger_prepared_data(gl_filters=None):
    """
    Build the data for the General Ledger statement print format.

    Preferred path: run the General Ledger report LIVE using the filters the
    user currently has applied (passed as `gl_filters` by the print flow), so
    the statement always matches exactly what was filtered on screen — a single
    invoice, a single member, a party, etc.

    Fallback: if no filters are supplied (e.g. the format is rendered outside
    the normal flow), fall back to the latest Prepared Report, and if none is
    ready, raise a clear "Rebuild first" message instead of crashing.
    """
    filters = _resolve_filters(gl_filters)

    if filters:
        data, applied_filters = _run_live(filters)
    else:
        data, applied_filters = _from_latest_prepared_report()

    return _shape(data, applied_filters)


def _resolve_filters(gl_filters):
    """Filters arrive either as an argument or on the request (form_dict)."""
    raw = gl_filters or frappe.form_dict.get("gl_filters")
    if not raw:
        return {}
    try:
        parsed = frappe.parse_json(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}
    # strip empty values so we don't pass blanks to the report
    if isinstance(parsed, dict):
        return {k: v for k, v in parsed.items() if v not in (None, "", [], {})}
    return {}


def _run_live(filters):
    """Run the General Ledger report synchronously with the given filters.

    Because our overrides are installed at import time, this uses the same
    custom GL logic (withholding handling, member-number tagging, member
    filter, etc.) that the on-screen report uses.
    """
    from frappe.desk.query_report import run

    result = run("General Ledger", filters=filters, ignore_prepared_report=True)
    data = (result or {}).get("result") or []
    return data, filters


def _from_latest_prepared_report():
    import json
    import gzip
    from frappe.utils.file_manager import get_file_path

    pr = frappe.get_all(
        "Prepared Report",
        filters={"report_name": "General Ledger"},
        fields=["name", "filters"],
        order_by="creation desc",
        limit=1,
    )
    if not pr:
        frappe.throw(
            _(
                "No generated General Ledger report was found. Open the General "
                "Ledger report, apply your filters, click Rebuild, wait for it to "
                "finish, then download the PDF."
            ),
            title=_("Report Not Ready"),
        )

    pr = pr[0]
    applied_filters = frappe.parse_json(pr.filters) if pr.filters else {}

    file_doc = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Prepared Report",
            "attached_to_name": pr.name,
        },
        fields=["file_url"],
        order_by="creation desc",
        limit=1,
    )
    if not file_doc:
        frappe.throw(
            _(
                "The General Ledger report is still generating. Wait for Rebuild "
                "to finish, then download the PDF."
            ),
            title=_("Report Not Ready"),
        )

    file_path = get_file_path(file_doc[0].file_url)
    try:
        with gzip.open(file_path, "rb") as gz:
            content = json.loads(gz.read().decode("utf-8"))
    except OSError:
        with open(file_path, "r") as f:
            content = json.load(f)

    data = content.get("result", []) or content.get("data", [])
    return data, applied_filters


def _shape(data, applied_filters):
    """Split the report result into opening / rows / total / closing, and apply
    the Payment Entry cheque-no and withholding-tax tweaks the statement needs.
    The GL report result is ordered [opening, ...rows..., total, closing]."""
    data = list(data or [])

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

    payment_cache = {}
    withholding_cache = {}

    for row in cleaned_data:
        if row.get("voucher_type") == "Payment Entry" and row.get("voucher_no"):
            pe_name = row.get("voucher_no")
            account_name = (row.get("account") or "").lower()
            against_account = (row.get("against") or "").lower()

            if row.get("party_type") == "Supplier" and (
                "withholding" in account_name or "withholding" in against_account
            ):
                if pe_name not in withholding_cache:
                    withholding_cache[pe_name] = frappe.db.get_value(
                        "Payment Entry", pe_name, "tax_withholding_category"
                    )
                tax_category = withholding_cache.get(pe_name)
                if tax_category:
                    match = re.search(r"(\d+(\.\d+)?)\s*%", tax_category)
                    if match:
                        row["remarks"] = f"Withholding Tax-{match.group(1)}%"
                row["cheque_no"] = None
            else:
                if pe_name not in payment_cache:
                    payment_cache[pe_name] = frappe.db.get_value(
                        "Payment Entry", pe_name, "reference_no"
                    )
                row["cheque_no"] = payment_cache.get(pe_name)

    return {
        "success": True,
        "applied_filters": applied_filters or {},
        "data": cleaned_data,
        "balance_details": {
            "opening": first_row,
            "total": second_last_row,
            "closing": last_row,
        },
    }