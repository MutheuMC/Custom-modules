from odoo import models, fields, api # type: ignore

class DocumentUploadWizard(models.TransientModel):
    _name = 'custom.document.upload.wizard'
    _description = 'Document Upload Wizard'

    name = fields.Char('Document Name')
    document_type = fields.Selection([
        ('file', 'File'),
        ('url', 'URL Link'),
    ], string='Type', default='file', required=True)
    
    # File fields
    file = fields.Binary('File', attachment=True)
    file_name = fields.Char('File Name')
    
    # URL field
    url = fields.Char('URL')
    
    # Organization
    folder_id = fields.Many2one('custom.document.folder', 'Folder')
    tag_ids = fields.Many2many('custom.document.tag', string='Tags')
    description = fields.Text('Description')

    @api.onchange('file_name')
    def _onchange_file_name(self):
        if self.file_name and not self.name:
            self.name = self.file_name

    @api.onchange('url')
    def _onchange_url(self):
        if self.url and not self.name:
            self.name = self.url.split('/')[-1] or 'URL Document'

    def action_upload(self):
        """Create the document and close wizard"""
        self.ensure_one()
        
        vals = {
            'name': self.name or self.file_name or self.url or 'New Document',
            'document_type': self.document_type,
            'folder_id': self.folder_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'description': self.description,
        }
        
        if self.document_type == 'file':
            vals.update({
                'file': self.file,
                'file_name': self.file_name,
            })
        else:
            vals['url'] = self.url
            
        self.env['custom.document'].create(vals)
        
        return {'type': 'ir.actions.act_window_close'}