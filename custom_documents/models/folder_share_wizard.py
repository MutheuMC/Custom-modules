# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class CustomFolderShareWizard(models.TransientModel):
    _name = 'custom.folder.share.wizard'
    _description = 'Share Folder Wizard'

    # ---- Target folder ----
    folder_id = fields.Many2one(
        'custom.document.folder',
        string='Folder',
        required=True,
        readonly=True,
    )
    folder_name = fields.Char(
        string='Folder Name',
        related='folder_id.name',
        readonly=True,
    )

    # ---- Owner (display only) ----
    owner_user_id = fields.Many2one(
        'res.users',
        string='Owner User',
        compute='_compute_owner_fields',
        store=False,
    )
    owner_partner_id = fields.Many2one(
        'res.partner',
        string='Owner Partner',
        compute='_compute_owner_fields',
        store=False,
    )
    owner_email = fields.Char(
        string='Owner Email',
        compute='_compute_owner_fields',
        store=False,
    )
    owner_name = fields.Char(
        string='Owner Name',
        compute='_compute_owner_fields',
        store=False,
    )

    @api.depends('folder_id.user_id')
    def _compute_owner_fields(self):
        for wiz in self:
            user = wiz.folder_id.user_id
            if user:
                wiz.owner_user_id = user
                wiz.owner_partner_id = user.partner_id
                wiz.owner_email = user.partner_id.email or user.login
                wiz.owner_name = user.name
            else:
                wiz.owner_user_id = False
                wiz.owner_partner_id = False
                wiz.owner_email = False
                wiz.owner_name = False

    # ---- Inputs & live list ----
    partner_ids = fields.Many2many(
        'res.partner',
        string='Share with',
        domain=[('user_ids', '!=', False)],  # internal users only
        help='Select internal users to share this folder with',
    )

    # Live list bound to the real share lines on the folder
    share_ids = fields.One2many(
        comodel_name='custom.document.folder.share',
        inverse_name='folder_id',
        string='People with Access',
        related='folder_id.share_ids',
        readonly=False,  # allow inline remove
    )

    # ---- Internal users tracking ----
    internal_not_shared_count = fields.Integer(
        compute='_compute_internal_share_status',
        store=False
    )
    
    internal_fully_shared = fields.Boolean(
        compute='_compute_internal_share_status',
        store=False
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['folder_id'] = active_id
        return res

    # ---- Helper methods ----
    def _internal_partner_ids(self):
        """Get all active internal users (current/folder company)."""
        self.ensure_one()
        group_user = self.env.ref('base.group_user')
        company_id = self.folder_id.company_id.id or self.env.company.id
        
        users = self.env['res.users'].search([
            ('groups_id', 'in', group_user.id),
            ('active', '=', True),
            '|', 
                ('company_id', '=', company_id),
                ('company_ids', 'in', [company_id]),
        ])
        return set(users.mapped('partner_id').ids)

    @api.depends('folder_id', 'folder_id.share_ids.partner_id')
    def _compute_internal_share_status(self):
        """Compute how many internal users don't have access yet."""
        for wiz in self:
            if not wiz.folder_id:
                wiz.internal_not_shared_count = 0
                wiz.internal_fully_shared = False
                continue
            
            internal_set = wiz._internal_partner_ids()
            
            # Don't count the owner
            if wiz.owner_partner_id:
                internal_set.discard(wiz.owner_partner_id.id)
            
            # Get partners who already have access
            already = set(wiz.folder_id.share_ids.mapped('partner_id').ids)
            
            # Calculate who's missing
            to_add = internal_set - already
            
            wiz.internal_not_shared_count = len(to_add)
            wiz.internal_fully_shared = (len(to_add) == 0)

    # ---- Actions ----
    def action_share(self):
        """Create folder share rows for selected partners; keep wizard open."""
        self.ensure_one()
        folder = self.folder_id

        if not self.partner_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Selection'),
                    'message': _('Please select at least one person to share with.'),
                    'type': 'warning',
                }
            }

        existing_partner_ids = set(folder.share_ids.mapped('partner_id').ids)
        shared_count = 0
        
        for partner in self.partner_ids:
            if partner.id in existing_partner_ids:
                continue
            
            self.env['custom.document.folder.share'].create({
                'folder_id': folder.id,
                'partner_id': partner.id,
                'recursive': True,  # Default to include subfolders
            })
            shared_count += 1
            
            # Notify via chatter
            if hasattr(folder, 'message_post'):
                folder.message_post(
                    body=_('This folder has been shared with you by %s') % (folder.user_id.name,),
                    subject=_('Folder Shared: %s') % (folder.name,),
                    message_type='notification',
                    partner_ids=[partner.id],
                    subtype_xmlid='mail.mt_comment',
                )

        # Clear picker; list refreshes (related O2M)
        self.partner_ids = [(5, 0, 0)]

        # Show success notification
        if shared_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Folder shared with %s user(s)') % shared_count,
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': self._name,
                        'res_id': self.id,
                        'view_mode': 'form',
                        'target': 'new',
                        'name': _('Share "%s"') % folder.name,
                    }
                }
            }

        # Keep wizard open and refreshed
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Share "%s"') % folder.name,
        }

    def action_share_internal(self):
        """Share with ALL internal users, skip owner/duplicates, keep wizard open."""
        self.ensure_one()
        folder = self.folder_id
        
        # Get all internal partners
        internal = self._internal_partner_ids()
        
        # Don't share with owner
        if self.owner_partner_id:
            internal.discard(self.owner_partner_id.id)
        
        # Get existing shares
        already = set(folder.share_ids.mapped('partner_id').ids)
        
        # Calculate who needs access
        to_add = list(internal - already)
        
        if not to_add:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Already Shared'),
                    'message': _('This folder is already shared with all internal users.'),
                    'type': 'info',
                }
            }
        
        # Create shares
        self.env['custom.document.folder.share'].create(
            [{'folder_id': folder.id, 'partner_id': pid, 'recursive': True} 
             for pid in to_add]
        )
        
        # Send notification to all new recipients
        if hasattr(folder, 'message_post'):
            folder.message_post(
                body=_('This folder has been shared with all internal users by %s') % (folder.user_id.name,),
                subject=_('Folder Shared: %s') % (folder.name,),
                message_type='notification',
                partner_ids=to_add,
                subtype_xmlid='mail.mt_comment',
            )
        
        # Show success and reopen wizard
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Folder shared with %s internal users') % len(to_add),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                    'name': _('Share "%s"') % folder.name,
                }
            }
        }