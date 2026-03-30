# Copyright (c) 2024, Amir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, cstr


def execute(filters=None):
	"""
	تقرير دفتر الأستاذ المفصل - يعرض كل سطر من GL Entry بشكل منفصل
	Detailed General Ledger Report - Shows every GL Entry line separately
	"""
	if not filters:
		filters = {}
	
	validate_filters(filters)
	columns = get_columns(filters)
	data = get_data(filters)
	
	return columns, data


def validate_filters(filters):
	"""التحقق من صحة الفلاتر المطلوبة"""
	if not filters.get("company"):
		frappe.throw(_("Please select Company"))
	
	if not filters.get("from_date"):
		frappe.throw(_("Please select From Date"))
	
	if not filters.get("to_date"):
		frappe.throw(_("Please select To Date"))


def get_columns(filters):
	"""
	تعريف أعمدة التقرير - بنفس ترتيب الصورة المرفقة
	Columns definition - same order as the uploaded image
	"""
	columns = [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 140
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 160
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Party Name"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150
		},
		{
			"label": _("Debit"),
			"fieldname": "debit",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Credit"),
			"fieldname": "credit",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Balance"),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Note"),
			"fieldname": "remarks",
			"fieldtype": "Text",
			"width": 200
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 150
		},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"fieldtype": "Text",
			"width": 150
		},
		{
			"label": _("User Name"),
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120
		}
	]
	
	# إضافة أعمدة الأبعاد المحاسبية (Account Dimensions)
	accounting_dimensions = get_accounting_dimensions()
	for dimension in accounting_dimensions:
		columns.append({
			"label": _(dimension.get("label")),
			"fieldname": dimension.get("fieldname"),
			"fieldtype": "Link",
			"options": dimension.get("document_type"),
			"width": 120
		})
	
	# إضافة الحقول المخصصة (Custom Fields - مثل Sales Person)
	custom_fields = get_custom_fields()
	for field in custom_fields:
		columns.append({
			"label": _(field.get("label")),
			"fieldname": field.get("fieldname"),
			"fieldtype": field.get("fieldtype"),
			"options": field.get("options"),
			"width": 120
		})
	
	return columns


def get_data(filters):
	"""
	جلب البيانات من GL Entry مع حساب الرصيد
	Fetch data from GL Entry with running balance calculation
	
	الفرق الأساسي: هذا التقرير يعرض كل سطر من GL Entry بشكل منفصل
	Key difference: This report shows every GL Entry line separately
	"""
	conditions = get_conditions(filters)
	
	# جلب أسماء حقول الأبعاد المحاسبية
	accounting_dimensions = get_accounting_dimensions()
	dimension_fields = ", ".join([f"gle.{d.get('fieldname')}" for d in accounting_dimensions]) if accounting_dimensions else ""
	
	# جلب أسماء الحقول المخصصة
	custom_fields = get_custom_fields()
	custom_field_names = ", ".join([f"gle.{f.get('fieldname')}" for f in custom_fields]) if custom_fields else ""
	
	# بناء قائمة الحقول الإضافية
	additional_fields = []
	if dimension_fields:
		additional_fields.append(dimension_fields)
	if custom_field_names:
		additional_fields.append(custom_field_names)
	
	additional_fields_str = ", " + ", ".join(additional_fields) if additional_fields else ""
	
	# ============================================
	# الاستعلام الرئيسي - يجلب كل سطر بشكل منفصل
	# Main Query - Fetches every line separately
	# ============================================
	query = f"""
		SELECT
			gle.posting_date,
			gle.voucher_type,
			gle.voucher_no,
			gle.account,
			gle.party_type,
			gle.party,
			gle.debit,
			gle.credit,
			gle.remarks,
			gle.cost_center,
			gle.against,
			gle.project,
			gle.owner,
			gle.creation,
			gle.company
			{additional_fields_str}
		FROM
			`tabGL Entry` gle
		WHERE
			gle.docstatus = 1
			{conditions}
		ORDER BY
			gle.posting_date, gle.creation, gle.account, gle.name
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# ============================================
	# حساب الرصيد التراكمي
	# Calculate running balance
	# ============================================
	if filters.get("account"):
		# إذا كان هناك حساب محدد، نحسب رصيده التراكمي
		balance = get_opening_balance(filters)
		for row in data:
			balance += flt(row.debit) - flt(row.credit)
			row['balance'] = balance
	else:
		# إذا لم يكن هناك حساب محدد، نحسب الرصيد لكل حساب على حدة
		account_balances = {}
		for row in data:
			account = row.get('account')
			if account not in account_balances:
				# حساب الرصيد الافتتاحي لهذا الحساب
				account_balances[account] = get_opening_balance({
					**filters,
					'account': account
				})
			
			account_balances[account] += flt(row.debit) - flt(row.credit)
			row['balance'] = account_balances[account]
	
	return data


def get_opening_balance(filters):
	"""
	حساب الرصيد الافتتاحي قبل تاريخ البداية
	Calculate opening balance before start date
	"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("company = %(company)s")
	
	if filters.get("account"):
		conditions.append("account = %(account)s")
	
	if filters.get("cost_center"):
		conditions.append("cost_center = %(cost_center)s")
	
	if filters.get("from_date"):
		# الرصيد الافتتاحي = مجموع الحركات قبل تاريخ البداية
		opening_query = f"""
			SELECT
				SUM(debit) - SUM(credit) as opening_balance
			FROM
				`tabGL Entry`
			WHERE
				docstatus = 1
				AND posting_date < %(from_date)s
				{' AND ' + ' AND '.join(conditions) if conditions else ''}
		"""
		opening_balance = frappe.db.sql(opening_query, filters, as_dict=1)
		return flt(opening_balance[0].get('opening_balance')) if opening_balance else 0
	
	return 0


def get_conditions(filters):
	"""
	بناء شروط الاستعلام بناءً على الفلاتر
	Build query conditions based on filters
	"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("gle.company = %(company)s")
	
	if filters.get("from_date"):
		conditions.append("gle.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("gle.posting_date <= %(to_date)s")
	
	if filters.get("account"):
		conditions.append("gle.account = %(account)s")
	
	if filters.get("voucher_type"):
		conditions.append("gle.voucher_type = %(voucher_type)s")
	
	if filters.get("voucher_no"):
		conditions.append("gle.voucher_no = %(voucher_no)s")
	
	if filters.get("party_type"):
		conditions.append("gle.party_type = %(party_type)s")
	
	if filters.get("party"):
		conditions.append("gle.party = %(party)s")
	
	if filters.get("cost_center"):
		conditions.append("gle.cost_center = %(cost_center)s")
	
	if filters.get("project"):
		conditions.append("gle.project = %(project)s")
	
	if filters.get("owner"):
		conditions.append("gle.owner = %(owner)s")
	
	if filters.get("remarks"):
		conditions.append("gle.remarks LIKE %(remarks)s")
		filters["remarks"] = f"%{filters.get('remarks')}%"
	
	# فلاتر الأبعاد المحاسبية
	accounting_dimensions = get_accounting_dimensions()
	for dimension in accounting_dimensions:
		fieldname = dimension.get("fieldname")
		if filters.get(fieldname):
			conditions.append(f"gle.{fieldname} = %({fieldname})s")
	
	# فلاتر الحقول المخصصة (مثل Sales Person)
	custom_fields = get_custom_fields()
	for field in custom_fields:
		fieldname = field.get("fieldname")
		if filters.get(fieldname):
			conditions.append(f"gle.{fieldname} = %({fieldname})s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_accounting_dimensions():
	"""
	جلب الأبعاد المحاسبية المفعلة
	Get enabled accounting dimensions
	"""
	try:
		accounting_dimensions = frappe.get_all(
			"Accounting Dimension",
			filters={"disabled": 0},
			fields=["label", "fieldname", "document_type"]
		)
		return accounting_dimensions
	except:
		return []


def get_custom_fields():
	"""
	جلب الحقول المخصصة لـ GL Entry
	Get custom fields for GL Entry
	"""
	try:
		custom_fields = frappe.get_all(
			"Custom Field",
			filters={
				"dt": "GL Entry",
				"hidden": 0
			},
			fields=["label", "fieldname", "fieldtype", "options"],
			order_by="idx"
		)
		return custom_fields
	except:
		return []
