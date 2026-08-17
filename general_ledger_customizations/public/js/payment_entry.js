frappe.ui.form.on('Payment Entry', {
    paid_from: function (frm) {
        if (frm.doc.docstatus !== 0) return;
        fetch_outstanding_invoices(frm);
    },
    paid_to: function (frm) {
        if (frm.doc.docstatus !== 0) return;
        fetch_outstanding_invoices(frm);
    },
    paid_amount: function (frm) {
        if (frm.doc.docstatus !== 0) return;
        // user (or code) changed the total -> re-spread it across the included invoices
        distribute_allocations(frm);
    },
    before_save: function (frm) {
        if (frm.doc.docstatus !== 0) return;
        if (!(frm.doc.references || []).length) return;

        if (!frm.doc.references.some(function (r) { return r.custom_include; })) {
            frappe.throw(__("Please select at least one invoice using the Include checkbox."));
        }

        // final guarantee: re-derive allocations from Paid Amount, capped at each net
        distribute_allocations(frm);

        // Paid Amount = what actually got allocated (drop any un-allocatable remainder)
        let total = 0;
        frm.doc.references.forEach(function (r) {
            if (r.custom_include) total += flt(r.allocated_amount);
        });
        frm.doc.paid_amount = total;   // direct set, avoid re-trigger mid-save

        // keep only funded rows
        frm.doc.references = frm.doc.references.filter(function (r) {
            return r.custom_include && flt(r.allocated_amount) > 0;
        });
        frm.doc.references.forEach(function (r, i) { r.idx = i + 1; });

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
            if (frm.doc.docstatus !== 0) return;

            const is_pay = frm.doc.payment_type === 'Pay';
            frm.clear_table("references");

            r.message.forEach(function (row) {
                const child = frm.add_child("references", {
                    reference_doctype: row.voucher_type,
                    reference_name: row.voucher_no,
                    due_date: row.due_date,
                    total_amount: row.invoice_amount,
                    outstanding_amount: row.outstanding_amount,   // native, ERPNext owns this
                    allocated_amount: 0,
                    custom_include: 0,
                    account: row.account,
                    custom_outstanding: is_pay ? (row.custom_outstanding || row.outstanding_amount) : row.outstanding_amount,
                    custom_adjustment_rejection: is_pay ? (row.custom_adjustment_rejection || 0) : 0,
                    custom_awarded_amount: is_pay ? (row.custom_awarded_amount || row.invoice_amount) : 0,
                    custom_adjustment_locked: is_pay ? (row.custom_adjustment_locked || 0) : 0
                });

                if (child.custom_adjustment_locked) {
                    child._locked_adjustment = flt(child.custom_adjustment_rejection);
                    child._locked_awarded = flt(child.custom_awarded_amount);
                }
            });

            frm.set_value("paid_amount", 0);
            frm.refresh_field("references");
        }
    });
}

frappe.ui.form.on('Payment Entry Reference', {
    custom_include: function (frm, cdt, cdn) {
        if (frm.doc.docstatus !== 0) return;
        // include/exclude changed -> Paid Amount = full net of everything included
        set_paid_to_full(frm);
    },

    custom_adjustment_rejection: function (frm, cdt, cdn) {
        if (frm.doc.docstatus !== 0) return;
        if (frm.doc.payment_type !== 'Pay') return;
        const row = locals[cdt][cdn];

        if (row.custom_adjustment_locked) {
            row.custom_adjustment_rejection = flt(row._locked_adjustment);
            frm.refresh_field("references");
            frappe.msgprint(__("Adjustment / Rejection was already set on an earlier payment for this invoice and cannot be changed."));
            return;
        }
        apply_adjustment(frm, row, 'adjustment');
    },

    custom_awarded_amount: function (frm, cdt, cdn) {
        if (frm.doc.docstatus !== 0) return;
        if (frm.doc.payment_type !== 'Pay') return;
        const row = locals[cdt][cdn];

        if (row.custom_adjustment_locked) {
            row.custom_awarded_amount = flt(row._locked_awarded);
            frm.refresh_field("references");
            frappe.msgprint(__("Awarded Amount was already set on an earlier payment for this invoice and cannot be changed."));
            return;
        }
        apply_adjustment(frm, row, 'awarded');
    }
});

function apply_adjustment(frm, row, source) {
    const grand_total = flt(row.total_amount);
    let adjustment, awarded;

    if (source === 'awarded') {
        awarded = flt(row.custom_awarded_amount);
        if (awarded < 0) awarded = 0;
        if (awarded > grand_total) awarded = grand_total;
        adjustment = grand_total - awarded;
    } else {
        adjustment = flt(row.custom_adjustment_rejection);
        if (adjustment < 0) adjustment = 0;
        if (adjustment > grand_total) adjustment = grand_total;
        awarded = grand_total - adjustment;
    }

    row.custom_adjustment_rejection = adjustment;
    row.custom_awarded_amount = awarded;
    row.custom_outstanding = awarded;   // new display outstanding

    frm.refresh_field("references");
    set_paid_to_full(frm);                  // net changed -> re-total and re-spread
}

// Paid Amount = sum of net outstanding of all included invoices (then it auto-distributes)
function set_paid_to_full(frm) {
    let full = 0;
    (frm.doc.references || []).forEach(function (r) {
        if (r.custom_include) full += flt(r.custom_outstanding);
    });
    frm.set_value("paid_amount", full);   // triggers the paid_amount handler -> distribute
}

// Spread Paid Amount across included invoices, filling each up to its net, in row order
function distribute_allocations(frm) {
    (frm.doc.references || []).forEach(function (r) {
        if (!r.custom_include) r.allocated_amount = 0;
    });

    let remaining = flt(frm.doc.paid_amount);
    (frm.doc.references || []).forEach(function (row) {
        if (!row.custom_include) return;
        const cap = flt(row.custom_outstanding);
        let alloc = remaining >= cap ? cap : remaining;
        if (alloc < 0) alloc = 0;
        row.allocated_amount = alloc;
        remaining -= alloc;
    });

    frm.refresh_field("references");
}