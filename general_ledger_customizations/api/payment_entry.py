import frappe



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