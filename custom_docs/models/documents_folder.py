from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class DocumentsFolder(models.Model):
    _name = 'documents.folder'
    _description = 'Documents Folder'
    _parent_name = 'parent_folder_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, tracking=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    active = fields.Boolean(default=True, string='Active')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Hierarchy
    parent_folder_id = fields.Many2one('documents.folder', string='Parent Folder',
                                      ondelete='cascade', tracking=True)
    child_folder_ids = fields.One2many('documents.folder', 'parent_folder_id',
                                       string='Sub-folders')
    parent_path = fields.Char(index=True)
    
    # Access rights
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    read_group_ids = fields.Many2many('res.groups', 'documents_folder_read_groups',
                                      'folder_id', 'group_id', string='Read Groups')
    write_group_ids = fields.Many2many('res.groups', 'documents_folder_write_groups',
                                       'folder_id', 'group_id', string='Write Groups')
    user_specific = fields.Boolean(string='Own Documents Only',
                                  help='Limit users to see only their own documents')
    
    # Documents
    document_ids = fields.One2many('documents.document', 'folder_id', string='Documents')
    document_count = fields.Integer(compute='_compute_document_count', string='Document Count')
    
    # Tags
    tag_ids = fields.One2many('documents.tag', 'folder_id', string='Tags')
    
    # Workflow
    workflow_rule_ids = fields.One2many('documents.workflow.rule', 'folder_id',
                                       string='Workflow Rules')
    
    # Settings
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icon', default='fa-folder')
    color = fields.Integer(string='Color Index')
    
    @api.depends('name', 'parent_folder_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_folder_id:
                folder.complete_name = '%s / %s' % (folder.parent_folder_id.complete_name, folder.name)
            else:
                folder.complete_name = folder.name
    
    @api.depends('document_ids')
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)
    
    @api.constrains('parent_folder_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folders.'))
    
    def action_see_documents(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('folder_id', 'child_of', self.id)],
            'context': {
                'default_folder_id': self.id,
                'searchpanel_default_folder_id': self.id,
            }
        }