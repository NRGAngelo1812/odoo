from odoo import api, SUPERUSER_ID

from odoo.addons.l10n_cr_payroll_community.hooks import sync_salary_rules


def migrate(cr, version):
    """Move all migrated rules to the direct payroll date variables."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    sync_salary_rules(env)
