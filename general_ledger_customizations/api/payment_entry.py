import frappe



def validate_functions(self, method):
    set_forms_of_payment_remarks(self, method)
    set_claim_monthyear(self, method)
    
    
def set_forms_of_payment_remarks(self, method):
    if self.payment_type not in ("Pay", "Receive"):
        return

    old_doc = self.get_doc_before_save()

    # New document
    if not old_doc:
        self.remarks = self.custom_forms_of_payment or ""
        return

    # Payment type changed -> reset remarks
    if old_doc.custom_forms_of_payment != self.custom_forms_of_payment:
        self.remarks = self.custom_forms_of_payment or ""



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