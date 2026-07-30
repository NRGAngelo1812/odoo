from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


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
        if self.condition_select != "python":
            return super()._satisfy_condition(localdict)

        self.ensure_one()
        try:
            # Odoo 19 mutates the supplied context directly. The obsolete
            # ``nocopy`` argument from older versions must not be passed.
            safe_eval(self.condition_python, localdict, mode="exec")
            return bool(localdict.get("result", False))
        except Exception as error:
            raise UserError(
                _(
                    "Wrong python condition defined for salary rule "
                    "%(name)s (%(code)s).\n\nTechnical detail: %(error)s",
                    name=self.name,
                    code=self.code,
                    error=str(error),
                )
            ) from error
