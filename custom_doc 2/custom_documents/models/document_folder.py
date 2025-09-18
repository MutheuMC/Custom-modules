from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DocumentFolder(models.Model):
    _name = 'custom.document.folder'
    _description = 'Document Folder'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char('Folder Name', required=True)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True, recursive=True)
    parent_id = fields.Many2one(
        'custom.document.folder', 'Parent Folder',
        index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'custom.document.folder', 'parent_id', 'Child Folders')
    document_ids = fields.One2many(
        'custom.document', 'folder_id', 'Documents')
    document_count = fields.Integer(
        'Document Count', compute='_compute_document_count')
    color = fields.Integer('Color')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company)
    user_id = fields.Many2one(
        'res.users', 'Owner',
        default=lambda self: self.env.user)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = '%s / %s' % (
                    folder.parent_id.complete_name, folder.name)
            else:
                folder.complete_name = folder.name

    @api.depends('document_ids')
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folders.'))

    def action_open_documents(self):
        """Open documents in this folder"""
        self.ensure_one()
        
        # Get the action for documents
        action = self.env['ir.actions.act_window']._for_xml_id('custom_documents.action_custom_document')
        
        # Update the action with folder-specific context and domain
        action.update({
            'name': _('Documents in %s') % self.name,
            'domain': [('folder_id', '=', self.id)],
            'context': {
                **self.env.context,
                'default_folder_id': self.id,
                'search_default_folder_id': self.id,
            }
        })
        
        return action
    
    def action_open_folder_tree(self):
        """Open subfolder tree view"""
        self.ensure_one()
        return {
            'name': _('Subfolders of %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document.folder',
            'view_mode': 'kanban,list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
            }
        }