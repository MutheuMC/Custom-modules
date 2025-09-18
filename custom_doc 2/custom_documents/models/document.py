import base64
import mimetypes
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CustomDocument(models.Model):
    _name = 'custom.document'
    _description = 'Custom Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Document Name', required=True, tracking=True)

    document_type = fields.Selection(
        [('file', 'File'), ('url', 'URL Link')],
        string='Type', default='file', required=True
    )

    # File fields
    file = fields.Binary('File', attachment=True)
    file_name = fields.Char('File Name')
    file_size = fields.Integer('File Size', compute='_compute_file_size')
    mimetype = fields.Char('MIME Type')

    
    is_pdf = fields.Boolean(compute="_compute_is_pdf", store=False)

    # URL fields
    url = fields.Char('URL')

    # Organization fields
    folder_id = fields.Many2one('custom.document.folder', 'Folder', ondelete='cascade', index=True)

    # Meta fields
    description = fields.Text('Description')
    tag_ids = fields.Many2many('custom.document.tag', string='Tags')
    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    # Additional fields
    active = fields.Boolean('Active', default=True)
    color = fields.Integer('Color')
    priority = fields.Selection([('0', 'Normal'), ('1', 'High')], string='Priority', default='0')

    # Computed fields
    is_locked = fields.Boolean('Locked', default=False)
    locked_by = fields.Many2one('res.users', 'Locked By')
    
    # New field for PDF viewing
    file_view_url = fields.Char('File View URL', compute='_compute_file_view_url')

    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            if rec.file:
                try:
                    rec.file_size = len(base64.b64decode(rec.file))
                except Exception:
                    rec.file_size = 0
            else:
                rec.file_size = 0
                
    @api.depends('document_type', 'file')
    def _compute_file_view_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.document_type == 'file' and rec.file:
                rec.file_view_url = f"{base_url}/web/content/custom.document/{rec.id}/file/{rec.file_name or 'document'}"
            else:
                rec.file_view_url = False

    @api.constrains('document_type', 'file', 'url')
    def _check_document_data(self):
        for rec in self:
            if rec.document_type == 'file' and not rec.file:
                raise ValidationError(_('Please upload a file.'))
            if rec.document_type == 'url' and not rec.url:
                raise ValidationError(_('Please provide a URL.'))
            

    @api.depends('document_type', 'mimetype', 'file_name')
    def _compute_is_pdf(self):
        for rec in self:
            name = (rec.file_name or '').lower()
            mt = (rec.mimetype or '').lower()
            rec.is_pdf = (
                rec.document_type == 'file' and
                ('pdf' in mt or name.endswith('.pdf'))
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_type') == 'url' and vals.get('url') and not vals.get('name'):
                vals['name'] = vals['url'].split('/')[-1] or _('URL Document')
            elif vals.get('file_name') and not vals.get('name'):
                vals['name'] = vals['file_name']
                
            # Detect MIME type for files
            if vals.get('file') and not vals.get('mimetype'):
                if vals.get('file_name'):
                    mimetype, encoding = mimetypes.guess_type(vals['file_name'])
                    if mimetype:
                        vals['mimetype'] = mimetype
        return super().create(vals_list)
        
    def write(self, vals):
        if vals.get('file') and not vals.get('mimetype'):
            # If we are updating the file and not providing mimetype, try to detect
            file_name = vals.get('file_name') or self.file_name
            if file_name:
                mimetype, encoding = mimetypes.guess_type(file_name)
                if mimetype:
                    vals['mimetype'] = mimetype
        return super().write(vals)

    def action_download(self):
        self.ensure_one()
        if self.document_type == 'file':
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{self._name}/{self.id}/file/{self.file_name or ''}?download=true",
                'target': 'self',
            }
        if self.document_type == 'url':
            return {'type': 'ir.actions.act_url', 'url': self.url, 'target': 'new'}
            
    def action_view_file(self):
        self.ensure_one()
        if self.document_type == 'file' and self.file:
            if self.mimetype == 'application/pdf':
                # For PDFs, we'll open in the same tab
                return {
                    'type': 'ir.actions.act_url',
                    'url': self.file_view_url,
                    'target': 'self',
                }
            else:
                # For other files, use download
                return self.action_download()
        return False

    def action_lock(self):
        self.ensure_one()
        if self.is_locked and self.locked_by and self.locked_by != self.env.user:
            raise UserError(_('This document is locked by %s') % self.locked_by.name)
        self.write({
            'is_locked': not self.is_locked,
            'locked_by': self.env.user.id if not self.is_locked else False,
        })