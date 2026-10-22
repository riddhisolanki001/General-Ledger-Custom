// General Ledger desk customizations
// -------------------------------------------------------------------------
// 1) Adds a "Format" dropdown (Claims | Refunds) to the Print Settings popup
//    of the General Ledger report and routes the PDF to the matching layout.
// 2) Adds Member Number, Member Policy Number and Invoice Number filters to the
//    General Ledger report (placed with the other text filters, before the
//    checkbox filters).
// 3) When generating the PDF, injects the current on-screen filters (and the
//    chosen format) into the HTML as markers, so the statement is generated
//    LIVE from exactly what was filtered (single invoice / member / policy /
//    party), instead of the latest Prepared Report.
//
// render_pdf() only forwards html + orientation to the server, so both the
// format choice and the filters ride inside the HTML as marker comments that
// the backend (pdf_customization.custom_report_to_pdf) reads.
// -------------------------------------------------------------------------
(function () {
	const GL_REPORT = "General Ledger";
	let gl_format_type = "Claims"; // remembered between the popup and the PDF POST

	// Extra filters added to the General Ledger report.
	const GL_EXTRA_FILTERS = [
		{ fieldname: "member_number", label: __("Member Number"), fieldtype: "Data" },
		{ fieldname: "custom_member_policy_number", label: __("Member Policy Number"), fieldtype: "Data" },
		{ fieldname: "bill_no", label: __("Invoice Number"), fieldtype: "Data" },
	];

	function current_report_name() {
		try {
			if (frappe.query_report && frappe.query_report.report_name) {
				return frappe.query_report.report_name;
			}
			const route = frappe.get_route ? frappe.get_route() : [];
			return route && route.length > 1 ? route[1] : "";
		} catch (e) {
			return "";
		}
	}

	function current_filters() {
		try {
			if (
				frappe.query_report &&
				current_report_name() === GL_REPORT &&
				typeof frappe.query_report.get_filter_values === "function"
			) {
				return frappe.query_report.get_filter_values() || {};
			}
		} catch (e) {
			/* no-op */
		}
		return {};
	}

	// UTF-8 safe base64 so JSON braces/quotes survive inside an HTML comment.
	function b64(str) {
		return btoa(unescape(encodeURIComponent(str)));
	}

	// ----- 1) Add the extra filters to the GL report -------------------------
	// The report's own script assigns frappe.query_reports["General Ledger"]
	// when the report page loads (after this file). We intercept that assignment
	// so our filters are added whenever the report object is set, and also
	// augment it if it already exists. The fields are inserted just before the
	// first checkbox (Check) filter so they sit with the other text/select
	// filters instead of at the very end.
	function add_gl_filters(report_obj) {
		try {
			if (!report_obj || !Array.isArray(report_obj.filters)) return report_obj;

			let insert_at = report_obj.filters.findIndex((f) => f && f.fieldtype === "Check");
			if (insert_at < 0) insert_at = report_obj.filters.length;

			GL_EXTRA_FILTERS.forEach((f) => {
				const exists = report_obj.filters.some((x) => x && x.fieldname === f.fieldname);
				if (!exists) {
					report_obj.filters.splice(insert_at, 0, f);
					insert_at += 1;
				}
			});
		} catch (e) {
			console.warn("[GL] could not add filters", e);
		}
		return report_obj;
	}

	try {
		frappe.provide("frappe.query_reports");
		if (frappe.query_reports[GL_REPORT]) {
			add_gl_filters(frappe.query_reports[GL_REPORT]);
		}
		let _store = frappe.query_reports[GL_REPORT];
		Object.defineProperty(frappe.query_reports, GL_REPORT, {
			configurable: true,
			enumerable: true,
			get() {
				return _store;
			},
			set(v) {
				_store = add_gl_filters(v);
			},
		});
	} catch (e) {
		console.warn("[GL] filter hook failed", e);
	}

	// ----- 2) Add the "Format" dropdown to the Print Settings popup -----------
	const _get_print_settings = frappe.ui.get_print_settings;
	frappe.ui.get_print_settings = function (...args) {
		if (current_report_name() !== GL_REPORT) {
			return _get_print_settings.apply(this, args);
		}

		gl_format_type = "Claims"; // reset each time the popup opens

		const _prompt = frappe.prompt;
		frappe.prompt = function (fields, callback, title, primary_label) {
			if (Array.isArray(fields)) {
				fields.splice(1, 0, {
					fieldtype: "Select",
					fieldname: "gl_format_type",
					label: __("Format"),
					options: ["Claims", "Refunds"],
					default: "Claims",
					onchange() {
						try {
							gl_format_type = this.get_value() || "Claims";
						} catch (e) {
							/* no-op */
						}
					},
				});
			}
			const _callback = function (settings) {
				gl_format_type = (settings && settings.gl_format_type) || "Claims";
				return callback(settings);
			};
			return _prompt.call(this, fields, _callback, title, primary_label);
		};

		try {
			return _get_print_settings.apply(this, args);
		} finally {
			frappe.prompt = _prompt;
		}
	};

	// ----- 3) Inject format + filters markers into the PDF html ---------------
	const _render_pdf = frappe.render_pdf;
	frappe.render_pdf = function (html, opts = {}) {
		try {
			if (current_report_name() === GL_REPORT && typeof html === "string") {
				html = html.replace(/<!--\s*GL_FORMAT_TYPE:.*?-->/gi, "");
				html = html.replace(/<!--\s*GL_FILTERS:.*?-->/gi, "");

				const filters_marker =
					"<!-- GL_FILTERS:" + b64(JSON.stringify(current_filters())) + " -->";
				const format_marker =
					"<!-- GL_FORMAT_TYPE: " + (gl_format_type || "Claims") + " -->";

				html = format_marker + filters_marker + html;
			}
		} catch (e) {
			console.error("[GL] marker injection failed", e);
		}
		return _render_pdf.call(this, html, opts);
	};
})();