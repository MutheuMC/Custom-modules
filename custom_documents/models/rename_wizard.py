from odoo import api, models, fields, _
from odoo.exceptions import UserError

class CustomDocumentRenameWizard(models.TransientModel):
    _name = 'custom.document.rename.wizard'
    _description = 'Rename Document Wizard'

    document_id = fields.Many2one('custom.document', required=True, readonly=True)
    new_name = fields.Char('New name', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        doc_id = self.env.context.get('default_document_id') or self.env.context.get('active_id')
        if doc_id:
            res.setdefault('document_id', doc_id)
            if 'new_name' in fields_list and not res.get('new_name'):
                res['new_name'] = self.env['custom.document'].browse(doc_id).name or ''
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.new_name:
            raise UserError(_("Please provide a name."))
        self.document_id.sudo().write({'name': self.new_name})
        return {'type': 'ir.actions.act_window_close'}
