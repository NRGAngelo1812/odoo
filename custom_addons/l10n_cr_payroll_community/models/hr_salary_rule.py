from odoo import models


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    def _satisfy_condition(self, localdict):
        """Evaluate the two fortnight rules without safe_eval."""
        self.ensure_one()
        if self.code not in {"RENQ1", "RENQ2"}:
            return super()._satisfy_condition(localdict)

        date_from = localdict.get("date_from")
        if not date_from:
            payslip_wrapper = localdict.get("payslip")
            current_payslip = getattr(payslip_wrapper, "dict", False)
            date_from = getattr(current_payslip, "date_from", False)
        if not date_from:
            return False

        is_first_fortnight = date_from.day == 1
        return is_first_fortnight if self.code == "RENQ1" else not is_first_fortnight
