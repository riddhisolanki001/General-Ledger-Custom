// General Ledger – Claims / Refunds print-format selector  (DEBUG BUILD)
// -------------------------------------------------------------------------
// TEMPORARY diagnostic version. Same logic as the production file, but:
//   * logs every step to the browser console with a [GL-PDF] prefix
//   * surfaces errors (console.error + msgprint) instead of swallowing them
//   * exposes window.glPdfDebug so you can inspect the last captured state
//
// Use: replace gl_print_format_selector.js with this file, run
//   bench build --app general_ledger_customizations
// hard-refresh the browser (Ctrl+Shift+R), open DevTools > Console, then try
// to download. Revert to the production file once diagnosed.
// -------------------------------------------------------------------------
(function () {
	const GL_REPORT = "General Ledger";
	const TAG = "[GL-PDF]";
	let gl_format_type = "Claims";

	window.glPdfDebug = { gl_format_type, last_report: null, render_pdf_called: false };

	console.log(TAG, "debug script loaded");

	function current_report_name() {
		try {
			if (frappe.query_report && frappe.query_report.report_name) {
				return frappe.query_report.report_name;
			}
			const route = frappe.get_route ? frappe.get_route() : [];
			return route && route.length > 1 ? route[1] : "";
		} catch (e) {
			console.error(TAG, "current_report_name failed", e);
			return "";
		}
	}

	// 1) Inject the "Format" dropdown into the Print Settings popup.
	const _get_print_settings = frappe.ui.get_print_settings;
	frappe.ui.get_print_settings = function (...args) {
		const rpt = current_report_name();
		window.glPdfDebug.last_report = rpt;
		console.log(TAG, "get_print_settings opened. report =", JSON.stringify(rpt));

		if (rpt !== GL_REPORT) {
			console.log(TAG, "not the General Ledger report -> leaving popup untouched");
			return _get_print_settings.apply(this, args);
		}

		gl_format_type = "Claims";
		window.glPdfDebug.gl_format_type = gl_format_type;

		const _prompt = frappe.prompt;
		let patched_fired = false;
		frappe.prompt = function (fields, callback, title, primary_label) {
			patched_fired = true;
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
							window.glPdfDebug.gl_format_type = gl_format_type;
							console.log(TAG, "dropdown changed ->", gl_format_type);
						} catch (e) {
							console.error(TAG, "onchange failed", e);
						}
					},
				});
				console.log(TAG, "Format field spliced into popup. fieldcount =", fields.length);
			} else {
				console.warn(TAG, "prompt fields is not an array; cannot add Format field", fields);
			}
			const _callback = function (settings) {
				gl_format_type = (settings && settings.gl_format_type) || "Claims";
				window.glPdfDebug.gl_format_type = gl_format_type;
				console.log(TAG, "Submit clicked. captured gl_format_type =", gl_format_type, settings);
				return callback(settings);
			};
			return _prompt.call(this, fields, _callback, title, primary_label);
		};

		try {
			return _get_print_settings.apply(this, args);
		} finally {
			frappe.prompt = _prompt;
			if (!patched_fired) {
				console.warn(
					TAG,
					"get_print_settings did NOT call frappe.prompt in this version -> the Format field was not added. The dropdown you see is Frappe's built-in 'Print Format' field."
				);
			}
		}
	};

	// 2) Carry the choice inside the HTML so the backend override can read it.
	const _render_pdf = frappe.render_pdf;
	frappe.render_pdf = function (html, opts = {}) {
		window.glPdfDebug.render_pdf_called = true;
		const rpt = current_report_name();
		console.log(TAG, "render_pdf called. report =", JSON.stringify(rpt), "html_len =", (html || "").length);
		try {
			if (rpt === GL_REPORT && typeof html === "string") {
				const has_title = /<title>(.*?)<\/title>/i.test(html);
				html = html.replace(/<!--\s*GL_FORMAT_TYPE:.*?-->/gi, "");
				html = "<!-- GL_FORMAT_TYPE: " + (gl_format_type || "Claims") + " -->" + html;
				console.log(
					TAG,
					"marker injected ->",
					gl_format_type,
					"| <title> present in html:",
					has_title
				);
				if (!has_title) {
					console.warn(
						TAG,
						"No <title> in the html — the backend keys the GL branch off <title>, so it may not match."
					);
				}
			}
		} catch (e) {
			console.error(TAG, "marker injection failed", e);
			frappe.msgprint("GL-PDF marker injection failed: " + e.message);
		}
		return _render_pdf.call(this, html, opts);
	};

	// Surface the fact that render_pdf never ran after a submit, which means the
	// PDF path in this Frappe version does not go through frappe.render_pdf.
	console.log(TAG, "wrappers installed. After clicking Submit, expect a 'render_pdf called' line.");
})();