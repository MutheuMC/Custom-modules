import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CustomDocument(models.Model):
    _name = 'custom.document'
    _description = 'Custom Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Document Name', required=True, tracking=True)
    document_type = fields.Selection([
        ('file', 'File'),
        ('url', 'URL Link'),
    ], string='Type', default='file', required=True)
    
    # File fields
    file = fields.Binary('File', attachment=True)
    file_name = fields.Char('File Name')
    file_size = fields.Integer('File Size', compute='_compute_file_size')
    mimetype = fields.Char('MIME Type')
    
    # URL fields
    url = fields.Char('URL')
    
    # Organization fields
    folder_id = fields.Many2one(
        'custom.document.folder', 'Folder',
        ondelete='cascade', index=True)
    
    # Meta fields
    description = fields.Text('Description')
    tag_ids = fields.Many2many('custom.document.tag', string='Tags')
    user_id = fields.Many2one(
        'res.users', 'Owner',
        default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company)
    
    # Additional fields
    active = fields.Boolean('Active', default=True)
    color = fields.Integer('Color')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
    ], string='Priority', default='0')
    
    # Computed fields
    is_locked = fields.Boolean('Locked', default=False)
    locked_by = fields.Many2one('res.users', 'Locked By')

    @api.depends('file')
    def _compute_file_size(self):
        for record in self:
            if record.file:
                record.file_size = len(base64.b64decode(record.file))
            else:
                record.file_size = 0

    @api.constrains('document_type', 'file', 'url')
    def _check_document_data(self):
        for record in self:
            if record.document_type == 'file' and not record.file:
                raise ValidationError(_('Please upload a file.'))
            elif record.document_type == 'url' and not record.url:
                raise ValidationError(_('Please provide a URL.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_type') == 'url' and vals.get('url'):
                if not vals.get('name'):
                    vals['name'] = vals['url'].split('/')[-1] or 'URL Document'
            elif vals.get('file_name') and not vals.get('name'):
                vals['name'] = vals['file_name']
        return super().create(vals_list)

    def action_download(self):
        self.ensure_one()
        if self.document_type == 'file':
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{self._name}/{self.id}/file/{self.file_name or ''}?download=true",
                'target': 'self',
            }
        elif self.document_type == 'url':
            return {'type': 'ir.actions.act_url', 'url': self.url, 'target': 'new'}


    def action_lock(self):
        self.ensure_one()
        if self.is_locked and self.locked_by != self.env.user:
            raise UserError(_('This document is locked by %s') % self.locked_by.name)
        self.write({
            'is_locked': not self.is_locked,
            'locked_by': self.env.user.id if not self.is_locked else False,
        })

class DocumentTag(models.Model):
    _name = 'custom.document.tag'
    _description = 'Document Tag'

    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color')
    document_ids = fields.Many2many('custom.document', string='Documents')