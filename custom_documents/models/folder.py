from odoo import models, fields, api

class DocumentFolder(models.Model):
    _name = 'document.folder'
    _description = 'Document Folder'
    _order = 'sequence, name'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char(string='Folder Name', required=True)
    complete_name = fields.Char(
        string='Complete Name', compute='_compute_complete_name',
        store=True, recursive=True)
    parent_id = fields.Many2one(
        'document.folder', string='Parent Folder', ondelete='cascade')
    parent_path = fields.Char(index=True, unaccent=False)
    children_ids = fields.One2many(
        'document.folder', 'parent_id', string='Subfolders')
    document_ids = fields.One2many(
        'document.document', 'folder_id', string='Documents')
    document_count = fields.Integer(
        string='Documents Count', compute='_compute_document_count')
    sequence = fields.Integer(default=10)
    description = fields.Text(string='Description')
    group_ids = fields.Many2many(
        'res.groups', string='Access Groups',
        help='Groups allowed to access this folder')
    user_ids = fields.Many2many(
        'res.users', string='Allowed Users',
        help='Users allowed to access this folder')
    color = fields.Integer(string='Color Index')

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


    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)