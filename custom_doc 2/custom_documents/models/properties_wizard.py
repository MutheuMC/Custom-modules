from odoo import models, fields, _

class CustomDocumentPropertiesWizard(models.TransientModel):
    _name = 'custom.document.properties.wizard'
    _description = 'Document Properties Wizard'

    document_id = fields.Many2one('custom.document', required=True, readonly=True)
    name = fields.Char('Name')
    tag_ids = fields.Many2many('custom.document.tag', string='Tags')
    folder_id = fields.Many2one('custom.document.folder', string='Folder')

    def action_save(self):
        self.ensure_one()
        vals = {
            'name': self.name,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'folder_id': self.folder_id.id if self.folder_id else False,
        }
        self.document_id.sudo().write(vals)
        return {'type': 'ir.actions.act_window_close'}
