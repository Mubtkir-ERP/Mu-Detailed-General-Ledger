// Copyright (c) 2024, Amir and contributors
// For license information, please see license.txt

frappe.query_reports["Detailed General Ledger"] = {
	"filters": [
		// ==========================================
		// الفلاتر الأساسية الإلزامية
		// Required Basic Filters
		// ==========================================
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		
		// ==========================================
		// الفلاتر الاختيارية - بنفس ترتيب الصورة
		// Optional Filters - Same order as image
		// ==========================================
		{
			"fieldname": "account",
			"label": __("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Account",
					"filters": {
						"company": company,
					}
				}
			}
		},
		{
			"fieldname": "voucher_type",
			"label": __("Voucher Type"),
			"fieldtype": "Select",
			"options": [
				"",
				"Journal Entry",
				"Sales Invoice",
				"Purchase Invoice",
				"Payment Entry",
				"Vouchers Entry",
				"Delivery Note",
				"Purchase Receipt",
				"Stock Entry",
				"Expense Claim",
				"Asset",
				"Loan Disbursement",
				"Loan Repayment"
			],
		},
		{
			"fieldname": "voucher_no",
			"label": __("Voucher No"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type",
			"on_change": function() {
				frappe.query_report.set_filter_value('party', "");
			}
		},
		{
			"fieldname": "party",
			"label": __("Party Name"),
			"fieldtype": "Dynamic Link",
			"get_options": function() {
				var party_type = frappe.query_report.get_filter_value('party_type');
				var party = frappe.query_report.get_filter_value('party');
				if(party && !party_type) {
					frappe.throw(__("Please select Party Type first"));
				}
				return party_type;
			}
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Cost Center",
					"filters": {
						"company": company,
					}
				}
			}
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Project",
					"filters": {
						"company": company,
					}
				}
			}
		},
		{
			"fieldname": "remarks",
			"label": __("Note / Remarks"),
			"fieldtype": "Data",
			"description": __("Search in remarks/notes field")
		},
		{
			"fieldname": "owner",
			"label": __("User Name"),
			"fieldtype": "Link",
			"options": "User"
		}
	],
	
	"onload": function(report) {
		// ==========================================
		// إضافة فلاتر الأبعاد المحاسبية ديناميكياً
		// Add Accounting Dimensions filters dynamically
		// ==========================================
		frappe.call({
			method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_accounting_dimensions",
			callback: function(r) {
				if (r.message) {
					r.message.forEach(function(dimension) {
						frappe.query_report.add_filter({
							"fieldname": dimension.fieldname,
							"label": __(dimension.label),
							"fieldtype": "Link",
							"options": dimension.document_type,
							"insert_after_index": frappe.query_report.filters.length
						});
					});
				}
			}
		});
		
		// ==========================================
		// إضافة فلاتر الحقول المخصصة ديناميكياً
		// Add Custom Fields filters dynamically
		// ==========================================
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Custom Field",
				filters: {
					dt: "GL Entry",
					hidden: 0
				},
				fields: ["label", "fieldname", "fieldtype", "options"],
				order_by: "idx"
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					r.message.forEach(function(field) {
						frappe.query_report.add_filter({
							"fieldname": field.fieldname,
							"label": __(field.label),
							"fieldtype": field.fieldtype,
							"options": field.options || "",
							"insert_after_index": frappe.query_report.filters.length
						});
					});
				}
			}
		});
	},
	
	// ==========================================
	// التلوين البصري للبيانات
	// Visual color formatting
	// ==========================================
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// تلوين الأرصدة السالبة باللون الأحمر
		if (column.fieldname == "balance" && data && data.balance < 0) {
			value = "<span style='color:red; font-weight:bold'>" + value + "</span>";
		}
		
		// تلوين المدين بالأخضر
		if (column.fieldname == "debit" && data && data.debit > 0) {
			value = "<span style='color:green; font-weight:bold'>" + value + "</span>";
		}
		
		// تلوين الدائن بالأزرق
		if (column.fieldname == "credit" && data && data.credit > 0) {
			value = "<span style='color:blue; font-weight:bold'>" + value + "</span>";
		}
		
		// تلوين نوع السند "Vouchers Entry" بالبرتقالي للتمييز
		if (column.fieldname == "voucher_type" && data && data.voucher_type == "Vouchers Entry") {
			value = "<span style='color:darkorange; font-weight:bold'>" + value + "</span>";
		}
		
		return value;
	}
};
