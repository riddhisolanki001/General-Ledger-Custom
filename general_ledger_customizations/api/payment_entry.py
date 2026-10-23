import frappe
from frappe.utils import flt
from erpnext.accounts.doctype.payment_entry.payment_entry import get_outstanding_reference_documents
from datetime import datetime, timedelta


@frappe.whitelist()
def fetch_outstanding_invoices_custom(posting_date, company, party_type, payment_type, party, party_account):
    try:
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
            "get_outstanding_invoices": True,
        }

        invoices = get_outstanding_reference_documents(args=args) or []

        # adjustment / awarded logic only applies to outgoing (Pay) payments
        if payment_type != "Pay":
            return invoices

        result = []
        for inv in invoices:
            grand_total = flt(inv.get("invoice_amount"))             # invoice grand total
            native_outstanding = flt(inv.get("outstanding_amount"))  # ERPNext's real outstanding

            # was this invoice already adjusted on an earlier SUBMITTED payment?
            prior = frappe.db.get_all(
                "Payment Entry Reference",
                filters={
                    "reference_doctype": inv.get("voucher_type"),
                    "reference_name": inv.get("voucher_no"),
                    "docstatus": 1,
                    "custom_adjustment_rejection": [">", 0],
                },
                fields=["custom_adjustment_rejection"],
                order_by="creation desc",
                limit=1,
            )

            adjustment = flt(prior[0].custom_adjustment_rejection) if prior else 0.0
            locked = 1 if prior else 0

            awarded = grand_total - adjustment                 # total the company will pay
            net_outstanding = native_outstanding - adjustment  # remaining of the awarded amount

            # awarded amount already fully paid -> nothing left, hide it
            if locked and net_outstanding <= 0:
                continue

            inv["custom_adjustment_rejection"] = adjustment
            inv["custom_awarded_amount"] = awarded
            inv["custom_outstanding"] = net_outstanding
            inv["custom_adjustment_locked"] = locked

            result.append(inv)

        return result

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="fetch_outstanding_invoices_custom",
        )

def validate_functions(self, method):
    set_forms_of_payment_remarks(self, method)
    set_claim_monthyear(self, method)
    
    
def set_forms_of_payment_remarks(self, method):
    if self.payment_type not in ("Pay", "Receive"):
        return

    payment = (self.custom_forms_of_payment or "").strip()
    remarks = (self.remarks or "").strip()

    old_doc = self.get_doc_before_save()

    # New document
    if not old_doc:
        self.remarks = f"{payment} {remarks}".strip() if remarks else payment
        return

    old_payment = (old_doc.custom_forms_of_payment or "").strip()

    # Payment selection changed
    if payment != old_payment:
        if remarks.startswith(old_payment):
            # User didn't modify remarks after previous save
            self.remarks = payment
        else:
            # User cleared/edited remarks manually
            self.remarks = f"{payment} {remarks}".strip()
        return

    # Same payment, ensure prefix exists
    if payment and not remarks.startswith(payment):
        self.remarks = f"{payment} {remarks}".strip()


def set_claim_monthyear(self, method):
    for row in self.references:
        row.custom_claim_monthyear = None

        if not row.reference_doctype or not row.reference_name:
            continue

        meta = frappe.get_meta(row.reference_doctype)

        if meta.has_field("custom_claim_monthyear"):
            row.custom_claim_monthyear = frappe.db.get_value(
                row.reference_doctype,
                row.reference_name,
                "custom_claim_monthyear",
            )
