from odoo import api, SUPERUSER_ID

from odoo.addons.l10n_cr_payroll_community.hooks import sync_salary_rules


def migrate(cr, version):
    """Restore and synchronize the Python conditions with date variables."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    sync_salary_rules(env)
