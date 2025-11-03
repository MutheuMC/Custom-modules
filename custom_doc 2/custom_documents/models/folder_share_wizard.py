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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['folder_id'] = active_id
        return res

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
        for partner in self.partner_ids:
            if partner.id in existing_partner_ids:
                continue
            self.env['custom.document.folder.share'].create({
                'folder_id': folder.id,
                'partner_id': partner.id,
            })
            # (Optional) notify
            folder.message_post(
                body=_('%s shared this folder with you') % (folder.user_id.name,),
                subject=_('Folder Shared: %s') % (folder.name,),
                message_type='notification',
                partner_ids=[partner.id],
                subtype_xmlid='mail.mt_comment',
            )

        # Clear picker; list refreshes (related O2M)
        self.partner_ids = [(5, 0, 0)]

        # Keep wizard open and refreshed
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Share "%s"') % folder.name,
        }
