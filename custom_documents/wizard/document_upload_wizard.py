from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

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

    @api.model
    def default_get(self, fields_list):
        """Override to set default folder from context"""
        res = super().default_get(fields_list)
        
        _logger.info("=== UPLOAD WIZARD CONTEXT ===")
        _logger.info(f"Full context: {self.env.context}")
        
        # Get folder from context
        folder_id = self.env.context.get('default_folder_id')
        _logger.info(f"default_folder_id: {folder_id}")
        
        # Try searchpanel context
        if not folder_id:
            folder_id = self.env.context.get('searchpanel_default_folder_id')
            _logger.info(f"searchpanel_default_folder_id: {folder_id}")
        
        # Try active_id (when called from folder form)
        if not folder_id:
            if self.env.context.get('active_model') == 'custom.document.folder':
                folder_id = self.env.context.get('active_id')
                _logger.info(f"active_id from folder: {folder_id}")
        
        if folder_id:
            res['folder_id'] = folder_id
            _logger.info(f"Setting folder_id to: {folder_id}")
        else:
            _logger.info("No folder_id found in context")
            
        return res

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
        
        return self.env['ir.actions.act_window']._for_xml_id(
            'custom_documents.action_custom_document'
        )