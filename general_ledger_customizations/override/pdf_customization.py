import frappe
import re
from frappe.utils.pdf import get_pdf as original_get_pdf
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import get_url


@frappe.whitelist()
def custom_report_to_pdf(html=None, orientation="Landscape", **kwargs):

    if not html:
        frappe.throw("HTML content is required")

    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    report_name = match.group(1).strip() if match else "Report"

    if report_name.lower() == "general ledger":
        report = frappe.get_doc("Report", "General Ledger")
        url = get_url()

        download_url = (
            f"{url}/api/method/frappe.utils.print_format.download_pdf"
            "?doctype=Report&name=General%20Ledger&format=General%20Ledger"
            "&no_letterhead=1&letterhead=No%20Letterhead&_lang=en-GB"
        )

        frappe.local.response.update({
            "type": "redirect",
            "location": download_url,
            "filename": f"{report_name}.pdf"
        })
        return

    make_access_log(file_type="PDF", method="PDF", page=html)
    frappe.local.response.filename = f"{report_name}.pdf"
    frappe.local.response.filecontent = original_get_pdf(html, {"orientation": orientation})
    frappe.local.response.type = "pdf"


import frappe.utils.print_format
frappe.utils.print_format.report_to_pdf = custom_report_to_pdf
