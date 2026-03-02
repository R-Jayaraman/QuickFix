import frappe

def job_card_permission_query(user):
    if "QF Technician" in frappe.get_roles(user):
        return f"""
            EXISTS (
                SELECT 1
                FROM `tabTechnician` t
                WHERE t.name = `tabJob Card`.assigned_technician
                AND t.user = '{user}'
            )
        """
    return None

def service_invoice_has_permission(doc, user):

    if "QF Manager" in frappe.get_roles(user):
        return True

    job = frappe.get_doc("Job Card", doc.job_card)

    if job.payment_status == "Paid":
        return True

    return False