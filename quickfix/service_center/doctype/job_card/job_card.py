import frappe
from frappe.model.document import Document


class JobCard(Document):

   
    def validate(self):

        if self.customer_phone and not self.customer_phone.isdigit():
            frappe.throw("Customer phone must contain only digits")

        if self.customer_phone and len(self.customer_phone) != 10:
            frappe.throw("Customer phone must be exactly 10 digits")

        if self.status in ["In Repair", "Ready for Delivery", "Delivered"]:
            if not self.assigned_technician:
                frappe.throw("Assigned Technician is required")

        parts_total = 0

        for row in self.parts_used:
            row.total_price = (row.quantity or 0) * (row.unit_price or 0)
            parts_total += row.total_price

        self.parts_total = parts_total

        if not self.labour_charge:
            settings = frappe.get_single("QuickFix Settings")
            self.labour_charge = settings.default_labour_charge or 0

        self.final_amount = self.parts_total + self.labour_charge

    def before_submit(self):

        # Only Ready for Delivery allowed
        if self.status != "Ready for Delivery":
            frappe.throw("Job Card must be Ready for Delivery to submit")

        # Check stock for each part
        for row in self.parts_used:

            stock = frappe.db.get_value(
                "Spare Part",
                row.part,
                "stock_qty"
            ) or 0

            if stock < row.quantity:
                frappe.throw(
                    f"Not enough stock for part {row.part}. Available: {stock}"
                )

    def on_submit(self):

        # Deduct stock
        for row in self.parts_used:

            stock = frappe.db.get_value(
                "Spare Part",
                row.part,
                "stock_qty"
            ) or 0

            new_stock = stock - row.quantity

            frappe.db.set_value(
                "Spare Part",
                row.part,
                "stock_qty",
                new_stock,
                update_modified=False
            )
            # ignore_permissions is acceptable because
            # this is system-driven stock deduction

        # Auto-create Service Invoice
        invoice = frappe.get_doc({
            "doctype": "Service Invoice",
            "job_card": self.name,
            "labour_charge": self.labour_charge,
            "parts_total": self.parts_total,
            "total_amount": self.final_amount
        })

        invoice.insert(ignore_permissions=True)


        # Realtime notification
        frappe.publish_realtime(
            "job_ready",
            {"job_card": self.name},
            user=self.owner
        )


        # Background email job
        frappe.enqueue(
            "quickfix.api.send_job_ready_email",
            job_card=self.name
        )

    def on_cancel(self):

        self.status = "Cancelled"

        # Restore stock
        for row in self.parts_used:

            stock = frappe.db.get_value(
                "Spare Part",
                row.part,
                "stock_qty"
            ) or 0

            frappe.db.set_value(
                "Spare Part",
                row.part,
                "stock_qty",
                stock + row.quantity
            )

        # Cancel linked invoice if exists
        invoice_name = frappe.db.get_value(
            "Service Invoice",
            {"job_card": self.name},
            "name"
        )

        if invoice_name:
            invoice = frappe.get_doc("Service Invoice", invoice_name)
            if invoice.docstatus == 1:
                invoice.cancel()


    def on_trash(self):

        if self.status not in ["Draft", "Cancelled"]:
            frappe.throw(
                "Only Draft or Cancelled Job Cards can be deleted"
            )

    def on_update(self):
        pass