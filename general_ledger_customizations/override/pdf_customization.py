    # import frappe
    # import re
    # from frappe.utils.pdf import get_pdf as original_get_pdf
    # from frappe.core.doctype.access_log.access_log import make_access_log
    # from frappe.utils import get_url


    # @frappe.whitelist()
    # def custom_report_to_pdf(html=None, orientation="Landscape", **kwargs):

    #     if not html:
    #         frappe.throw("HTML content is required")

    #     match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    #     report_name = match.group(1).strip() if match else "Report"

    #     if report_name.lower() == "general ledger":
    #         report = frappe.get_doc("Report", "General Ledger")
    #         url = get_url()

    #         # Get the default letterhead or specify a specific one
    #         letterhead = "General Ledger"

    #         download_url = (
    #             f"{url}/api/method/frappe.utils.print_format.download_pdf"
    #             f"?doctype=Report&name=General%20Ledger&format=General%20Ledger"
    #             f"&letterhead={letterhead}&_lang=en-GB"
    #         )

    #         frappe.local.response.update({
    #             "type": "redirect",
    #             "location": download_url,
    #             "filename": f"{report_name}.pdf"
    #         })
    #         return

    #     make_access_log(file_type="PDF", method="PDF", page=html)
    #     frappe.local.response.filename = f"{report_name}.pdf"
    #     frappe.local.response.filecontent = original_get_pdf(html, {"orientation": orientation})
    #     frappe.local.response.type = "pdf"


    # import frappe.utils.print_format
    # frappe.utils.print_format.report_to_pdf = custom_report_to_pdf


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

    # Handle General Ledger
    if report_name.lower() == "general ledger":
        url = get_url()
        letterhead = "General Ledger"

        download_url = (
            f"{url}/api/method/frappe.utils.print_format.download_pdf"
            f"?doctype=Report&name=General%20Ledger&format=General%20Ledger"
            f"&letterhead={letterhead}&_lang=en-GB"
        )

        frappe.local.response.update({
            "type": "redirect",
            "location": download_url,
            "filename": f"{report_name}.pdf"
        })
        return

    # Handle Balance Sheet
    if report_name.lower() == "balance sheet":
        url = get_url()
        letterhead = "General Ledger"
        
        download_url = (
            f"{url}/api/method/frappe.utils.print_format.download_pdf"
            f"?doctype=Report&name=Balance%20Sheet&format=Balance%20Sheet"
            f"&letterhead={letterhead}&_lang=en"
        )

        frappe.local.response.update({
            "type": "redirect",
            "location": download_url,
            "filename": f"{report_name}.pdf"
        })
        return
    
    # Handle Trial Balance
    if report_name.lower() == "trial balance":
        url = get_url()
        letterhead = "General Ledger" 
        
        download_url = (
            f"{url}/api/method/frappe.utils.print_format.download_pdf"
            f"?doctype=Report&name=Trial%20Balance&format=Trial%20Balance"
            f"&letterhead={letterhead}&_lang=en"
        )

        frappe.local.response.update({
            "type": "redirect",
            "location": download_url,
            "filename": f"{report_name}.pdf"
        })
        return

    # Default handling for other reports
    make_access_log(file_type="PDF", method="PDF", page=html)
    frappe.local.response.filename = f"{report_name}.pdf"
    frappe.local.response.filecontent = original_get_pdf(html, {"orientation": orientation})
    frappe.local.response.type = "pdf"


import frappe.utils.print_format
frappe.utils.print_format.report_to_pdf = custom_report_to_pdf