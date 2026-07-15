import frappe
import json
import gzip


def set_forms_of_payment_remarks(self, method):
    # Don't overwrite manual remarks
    if self.custom_remarks:
        return

    # Custom format only applies to Pay/Receive; keep core remarks otherwise
    if self.payment_type not in ("Pay", "Receive"):
        return

    remarks = f"{self.custom_forms_of_payment or ''} - {self.party_name or self.party}"

    for row in self.references:
        if row.reference_name:
            remarks += f", {row.reference_name}"

    self.remarks = remarks