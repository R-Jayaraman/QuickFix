import frappe
from frappe.model.document import Document

class SparePart(Document):

    def autoname(self):
        if not self.part_code:
            frappe.throw("Part Code is required")

        code = self.part_code.upper()

        series = frappe.model.naming.make_autoname("PART-.YYYY.-.####")

        self.name = f"{code}-{series}"

    def validate(self):
        if self.selling_price <= self.unit_cost:
            frappe.throw("Selling Price must be greater than Unit Cost")