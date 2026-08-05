frappe.ui.form.on('Payment Entry', {
    paid_from: function (frm) {
        if (frm.doc.docstatus !== 0) return;   // only fetch on a draft
        fetch_outstanding_invoices(frm);
    },
    paid_to: function (frm) {
        if (frm.doc.docstatus !== 0) return;
        fetch_outstanding_invoices(frm);
    },
    before_save: function (frm) {
        if (frm.doc.docstatus !== 0) return;

        // no references at all -> not using the custom flow, leave the doc alone
        if (!(frm.doc.references || []).length) return;

        // references exist but none checked -> user forgot to pick one
        if (!frm.doc.references.some(function (row) { return row.custom_include; })) {
            frappe.throw(__("Please select at least one invoice using the Include checkbox."));
        }

        // calculate_paid_amount_from_included(frm);

        frm.doc.references = frm.doc.references.filter(function (row) {
            return row.custom_include;
        });

        frm.doc.references.forEach(function (row, i) {
            row.idx = i + 1;
        });

        frm.refresh_field("references");
    }
});

function fetch_outstanding_invoices(frm) {
    if (!frm.doc.party) return;

    frappe.call({
        method: "general_ledger_customizations.api.payment_entry.fetch_outstanding_invoices_custom",
        args: {
            posting_date: frm.doc.posting_date,
            company: frm.doc.company,
            party_type: frm.doc.party_type,
            payment_type: frm.doc.payment_type,
            party: frm.doc.party,
            party_account: frm.doc.payment_type === 'Receive' ? frm.doc.paid_from : frm.doc.paid_to
        },
        callback: function (r) {
            if (!r.message) return;
            if (frm.doc.docstatus !== 0) return;   // guard the async callback too

            frm.clear_table("references");

            r.message.forEach(function (row) {
                frm.add_child("references", {
                    reference_doctype: row.voucher_type,
                    reference_name: row.voucher_no,
                    due_date: row.due_date,
                    total_amount: row.invoice_amount,
                    outstanding_amount: row.outstanding_amount,
                    allocated_amount: 0,
                    custom_include: 0,
                    account: row.account
                });
            });

            frm.set_value("paid_amount", 0);
            frm.refresh_field("references");
        }
    });
}

frappe.ui.form.on('Payment Entry Reference', {
    custom_include: function (frm, cdt, cdn) {
        if (frm.doc.docstatus !== 0) return;
        calculate_paid_amount_from_included(frm);
    }
});

function calculate_paid_amount_from_included(frm) {
    if (!(frm.doc.references || []).length) return;   // no rows -> don't touch paid_amount

    let total = 0;

    (frm.doc.references || []).forEach(function (row) {
        if (row.custom_include) {
            row.allocated_amount = flt(row.outstanding_amount);
            total += flt(row.outstanding_amount);
        } else {
            row.allocated_amount = 0;
        }
    });

    frm.set_value("paid_amount", total);
    frm.refresh_field("references");
}