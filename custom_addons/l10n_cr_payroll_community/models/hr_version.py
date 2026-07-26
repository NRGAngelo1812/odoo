from odoo import api, models


class HrVersion(models.Model):
    _inherit = "hr.version"

    @api.model
    def _get_whitelist_fields_from_template(self):
        """Copy payroll fields when applying an Odoo 19 contract template."""
        fields_to_copy = super()._get_whitelist_fields_from_template()
        return list(
            dict.fromkeys(
                fields_to_copy
                + [
                    "struct_id",
                    "schedule_pay",
                    "hra",
                    "travel_allowance",
                    "da",
                    "meal_allowance",
                    "medical_allowance",
                    "other_allowance",
                ]
            )
        )

    def get_all_structures(self):
        """Use the version structure or its contract-template structure."""
        structures = self.mapped("struct_id")
        structures |= self.mapped("contract_template_id.struct_id")
        if not structures:
            return []
        return list(set(structures._get_parent_structure().ids))
