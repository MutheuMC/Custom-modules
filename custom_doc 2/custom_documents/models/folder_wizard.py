from odoo import api, fields, models, _

class CustomDocumentFolderWizard(models.TransientModel):
    _name = "custom.document.folder.wizard"
    _description = "Create Folder Wizard"

    name = fields.Char(required=True, string="Folder Name")
    parent_id = fields.Many2one("custom.document.folder", string="Parent Folder")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get("active_model") == "custom.document.folder" and ctx.get("active_id"):
            res["parent_id"] = ctx["active_id"]
        return res

    def action_create(self):
        self.ensure_one()
        self.env["custom.document.folder"].create({
            "name": (self.name or "").strip(),
            "parent_id": self.parent_id.id or False,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
        })
        # show a toast, then refresh the underlying "Documents" view
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Folder created"),
                "message": self.name,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    

