from odoo import models, fields, _
from odoo.exceptions import UserError

class CustomDocumentRenameWizard(models.TransientModel):
    _name = 'custom.document.rename.wizard'
    _description = 'Rename Document Wizard'
    document_id = fields.Many2one('custom.document', required=True, readonly=True)
    new_name = fields.Char('New name', required=True)

    def action_apply(self):
        self.ensure_one()
        if not self.new_name:
            raise UserError(_("Please provide a name."))
        self.document_id.sudo().write({'name': self.new_name})
        return {'type': 'ir.actions.act_window_close'}
