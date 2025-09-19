# -*- coding: utf-8 -*-
from odoo import api, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        folder_model = self.env["custom.document.folder"].sudo()
        for emp in employees:
            # will also ensure Company root + Employees root
            folder_model._ensure_employee_folder(emp)
        return employees

    def write(self, vals):
        """Keep the employee folder in sync when the name/company changes."""
        res = super().write(vals)
        if any(k in vals for k in ("name", "company_id")):
            folder_model = self.env["custom.document.folder"].sudo()
            for emp in self:
                folder_model._ensure_employee_folder(emp)
        return res
