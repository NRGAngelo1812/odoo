from odoo import models


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    def _satisfy_condition(self, localdict):
        """Ensure payroll dates exist before evaluating Python conditions."""
        inputs_wrapper = localdict.get("inputs")

        def input_amount(code):
            input_line = (
                getattr(inputs_wrapper, "dict", {}).get(code)
                if inputs_wrapper
                else False
            )
            return input_line.amount if input_line else 0.0

        localdict["input_amount"] = input_amount
        if not localdict.get("date_from") or not localdict.get("date_to"):
            payslip_wrapper = localdict.get("payslip")
            current_payslip = getattr(payslip_wrapper, "dict", False)
            if current_payslip:
                localdict.setdefault("date_from", current_payslip.date_from)
                localdict.setdefault("date_to", current_payslip.date_to)
        return super()._satisfy_condition(localdict)
