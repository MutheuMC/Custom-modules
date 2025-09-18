from odoo import api, fields, models

class CustomDocumentFolderWizard(models.TransientModel):
    _name = "custom.document.folder.wizard"
    _description = "Create Folder Wizard"

    name = fields.Char(required=True, string="Folder Name")
    parent_id = fields.Many2one("custom.document.folder", string="Parent Folder")
    user_id = fields.Many2one("res.users", string="Owner", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    color = fields.Integer(string="Color", default=0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        # If opened from a folder form, prefill parent
        if ctx.get("active_model") == "custom.document.folder" and ctx.get("active_id"):
            res["parent_id"] = ctx["active_id"]
        return res

    def action_create(self):
        self.ensure_one()
        folder = self.env["custom.document.folder"].create({
            "name": self.name,
            "parent_id": self.parent_id.id,
            "user_id": self.user_id.id,
            "company_id": self.company_id.id if self.company_id else False,
            "color": self.color,
        })
        # Open the created folder
        return {'type': 'ir.actions.act_window_close'}
