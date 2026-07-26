from odoo import api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _load_contract_structure_inputs(self):
        """Copy the contract structure and rebuild the corresponding inputs."""
        if not self.contract_id or not self.date_from or not self.date_to:
            return
        structure = (
            self.contract_id.struct_id
            or self.contract_id.contract_template_id.struct_id
        )
        if structure:
            self.struct_id = structure
        if not self.struct_id:
            return
        input_values = self.get_inputs(
            self.contract_id, self.date_from, self.date_to
        )
        input_lines = self.input_line_ids.browse([])
        for values in input_values:
            input_lines += input_lines.new(values)
        self.input_line_ids = input_lines

    def _get_rules_for_inputs(self, contracts):
        structures = self.struct_id._get_parent_structure()
        if not structures:
            structure_ids = contracts.get_all_structures()
            structures = self.env["hr.payroll.structure"].browse(structure_ids)
        rule_ids = structures.get_all_rules()
        sorted_rule_ids = [
            rule_id for rule_id, _sequence in sorted(rule_ids, key=lambda item: item[1])
        ]
        return self.env["hr.salary.rule"].browse(sorted_rule_ids)

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Build inputs from the payslip structure, with contract fallback."""
        result = []
        inputs = self._get_rules_for_inputs(contracts).mapped("input_ids")
        for contract in contracts:
            for rule_input in inputs:
                result.append(
                    {
                        "name": rule_input.name,
                        "code": rule_input.code,
                        "contract_id": contract.id,
                        "date_from": date_from,
                        "date_to": date_to,
                    }
                )
        return result

    @api.onchange("struct_id")
    def _onchange_l10n_cr_structure_inputs(self):
        if not self.struct_id or not self.contract_id or not self.date_from or not self.date_to:
            return
        input_values = self.get_inputs(
            self.contract_id, self.date_from, self.date_to
        )
        input_lines = self.input_line_ids.browse([])
        for values in input_values:
            input_lines += input_lines.new(values)
        self.input_line_ids = input_lines

    @api.onchange("employee_id")
    def onchange_employee(self):
        result = super().onchange_employee()
        self._load_contract_structure_inputs()
        return result

    @api.onchange("contract_id")
    def onchange_contract_id(self):
        result = super().onchange_contract_id()
        self._load_contract_structure_inputs()
        return result
