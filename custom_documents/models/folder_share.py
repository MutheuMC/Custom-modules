from odoo import models, fields, api, _

class CustomDocumentFolderShare(models.Model):
    _name = 'custom.document.folder.share'
    _description = 'Folder Sharing'
    _rec_name = 'partner_id'

    folder_id = fields.Many2one(
        'custom.document.folder',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Shared With',
        required=True,
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        compute='_compute_user',
        store=True,
        index=True
    )
    
    recursive = fields.Boolean(
        string='Include Subfolders',
        default=True,
        help='Give access to all subfolders and documents inside'
    )

    email = fields.Char(
    string='Email',
    related='partner_id.email',
    readonly=True,
    store=True
)
    
    _sql_constraints = [
        ('unique_folder_partner',
         'UNIQUE(folder_id, partner_id)',
         'This person already has access to this folder!')
    ]

    @api.depends('partner_id')
    def _compute_user(self):
        for rec in self:
            rec.user_id = rec.partner_id.user_ids[:1] if rec.partner_id.user_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        # Send notification
        for rec in records:
            rec.folder_id.message_post(
                body=_('%s shared this folder with you') % rec.folder_id.user_id.name,
                subject=_('Folder Shared: %s') % rec.folder_id.name,
                message_type='notification',
                partner_ids=[rec.partner_id.id],
                subtype_xmlid='mail.mt_comment',
            )
            
            # Subscribe to folder updates
            rec.folder_id.message_subscribe(partner_ids=[rec.partner_id.id])
        
        return records


