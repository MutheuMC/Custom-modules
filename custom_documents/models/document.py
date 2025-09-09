from odoo import models, fields, api, _
from odoo.exceptions import AccessError

class DocumentDocument(models.Model):
    _name = 'document.document'
    _description = 'Document'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    folder_id = fields.Many2one(
        'document.folder', string='Folder', required=True)
    tag_ids = fields.Many2many(
        'document.tag', 'document_tag_rel',
        'document_id', 'tag_id', string='Tags')
    owner_id = fields.Many2one(
        'res.users', string='Owner', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Related Partner')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    res_model = fields.Char(string='Resource Model')
    res_id = fields.Integer(string='Resource ID')
    type = fields.Selection([
        ('binary', 'File'),
        ('url', 'URL'),
    ], string='Type', default='binary', required=True)
    url = fields.Char(string='URL')
    datas = fields.Binary(string='File Content')
    file_size = fields.Integer(string='File Size', compute='_compute_file_size')
    mimetype = fields.Char(string='Mime Type')
    extension = fields.Char(string='Extension', compute='_compute_extension')
    thumbnail = fields.Binary(string='Thumbnail')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    favorite_ids = fields.Many2many(
        'res.users', 'document_favorite_rel',
        'document_id', 'user_id', string='Favorite of')
    is_favorite = fields.Boolean(compute='_compute_is_favorite')

    @api.depends('datas')
    def _compute_file_size(self):
        for document in self:
            if document.datas:
                document.file_size = len(document.datas) * 3 / 4  # Base64 approximate
            else:
                document.file_size = 0

    @api.depends('name')
    def _compute_extension(self):
        for document in self:
            if document.name and '.' in document.name:
                document.extension = document.name.rsplit('.', 1)[1].lower()
            else:
                document.extension = False

    def _compute_is_favorite(self):
        for document in self:
            document.is_favorite = self.env.user in document.favorite_ids

    def action_toggle_favorite(self):
        self.ensure_one()
        if self.env.user in self.favorite_ids:
            self.write({'favorite_ids': [(3, self.env.user.id)]})
        else:
            self.write({'favorite_ids': [(4, self.env.user.id)]})

    def check_access_rule(self, operation):
        """Override to check folder access rights."""
        super().check_access_rule(operation)
        if self.folder_id:
            if not self.folder_id.group_ids and not self.folder_id.user_ids:
                return True
            if (self.env.user not in self.folder_id.user_ids and
                    not any(group in self.env.user.groups_id 
                    for group in self.folder_id.group_ids)):
                raise AccessError(_('You do not have access to this folder.'))
            


# class ResUsers(models.Model):
#     _inherit = 'res.users'

#     def _get_accessible_folder_ids(self):
#         for user in self:
#             folder_domain = ['|', ('user_ids', 'in', user.id), ('group_ids', 'in', user.groups_id.ids)]
#             user.document_folder_ids = self.env['document.folder'].search(folder_domain)

#     document_folder_ids = fields.Many2many(
#         'document.folder', 
#         string='Accessible Folders',
#         compute='_get_accessible_folder_ids'
#     )