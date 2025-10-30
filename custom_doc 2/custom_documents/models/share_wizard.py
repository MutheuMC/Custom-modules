# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

class CustomDocumentShareWizard(models.TransientModel):
    _name = 'custom.document.share.wizard'
    _description = 'Share Document Wizard'

    document_id = fields.Many2one(
        'custom.document',
        string='Document',
        required=True,
        readonly=True
    )
    
    document_name = fields.Char(
        related='document_id.name',
        string='Document Name',
        readonly=True
    )

    # Owner Display Fields - FIXED
    owner_user_id = fields.Many2one(
        'res.users',
        string='Owner User',
        compute='_compute_owner_fields',
        store=False
    )
    owner_partner_id = fields.Many2one(
        'res.partner',
        string='Owner Partner',
        compute='_compute_owner_fields',
        store=False
    )
    owner_email = fields.Char(
        string='Owner Email',
        compute='_compute_owner_fields',
        store=False
    )
    owner_name = fields.Char(
        string='Owner Name',
        compute='_compute_owner_fields',
        store=False
    )

    @api.depends('document_id', 'document_id.user_id')
    def _compute_owner_fields(self):
        """Compute owner fields from document"""
        for wizard in self:
            if wizard.document_id and wizard.document_id.user_id:
                owner = wizard.document_id.user_id
                wizard.owner_user_id = owner
                wizard.owner_partner_id = owner.partner_id
                wizard.owner_email = owner.partner_id.email or owner.login
                wizard.owner_name = owner.name
            else:
                wizard.owner_user_id = False
                wizard.owner_partner_id = False
                wizard.owner_email = False
                wizard.owner_name = False

    # Add People Section
    partner_ids = fields.Many2many(
        'res.partner',
        string='Add People',
        help='Select people to share with'
    )
   
    
    role = fields.Selection([
        ('viewer', 'Viewer'),
        ('commenter', 'Commenter'),
        ('editor', 'Editor')
    ], string='Role', default='viewer', required=True)

    # People with Access (inline editable)
    people_ids = fields.One2many(
        related='document_id.share_line_ids',
        string='People with Access',
        readonly=False
    )

    # General Access (Google Drive style)
    share_access = fields.Selection(
        related='document_id.share_access',
        string='General Access',
        readonly=False
    )

    # Share Links
    view_link = fields.Char(
        string='View Link',
        compute='_compute_links'
    )
    
    edit_link = fields.Char(
        string='Edit Link',
        compute='_compute_links'
    )

    all_people_with_access = fields.One2many(
        'custom.document.share.line',
        string="All People",
        compute='_compute_all_people_with_access'
    )


     # --- Helpers ---
    def _check_can_edit_role(self):
        """Only document owner or admins can change roles; never allow changing owner here."""
        for rec in self:
            current_user = self.env.user
            # If your document has an owner_user_id, gate changes behind that:
            if hasattr(rec.document_id, 'owner_user_id'):
                is_owner = (current_user == rec.document_id.owner_user_id)
            else:
                is_owner = current_user.has_group('base.group_system')  # fallback

            is_admin = current_user.has_group('custom_documents.group_document_admin') \
                       or current_user.has_group('base.group_system')

            if not (is_owner or is_admin):
                raise AccessError(_("Only the document owner or admins can change access levels."))

    def _apply_role_permissions(self):
        """Hook: map role -> your app permissions.
        If your code checks role at runtime, you can leave this empty.
        If you pre-compute ACLs, implement them here.
        """
        # Example stub: (replace with your own logic)
        # viewer: read only, commenter: read + comment, editor: read/write
        return True

    def write(self, vals):
        # Capture old roles for logging
        changing_role = 'role' in vals
        if changing_role:
            self._check_can_edit_role()
            old_roles = {rec.id: rec.role for rec in self}

        res = super().write(vals)

        if changing_role:
            for rec in self:
                rec._apply_role_permissions()
                # Optional: notify on the document (if it is mail.thread)
                if hasattr(rec.document_id, 'message_post'):
                    rec.document_id.message_post(
                        body=_("Access level for <b>%s</b> changed from <i>%s</i> to <i>%s</i>.") % (
                            rec.partner_id.display_name, old_roles.get(rec.id), rec.role
                        ),
                        subtype_xmlid='mail.mt_note',
                    )
        return res

    @api.depends('document_id', 'document_id.share_line_ids')
    def _compute_all_people_with_access(self):
        """Get all share lines for display"""
        for wizard in self:
            wizard.all_people_with_access = wizard.document_id.share_line_ids

    @api.depends('document_id', 'document_id.share_access')
    def _compute_links(self):
        """Generate shareable links"""
        for wizard in self:
            if wizard.document_id:
                wizard.view_link = wizard.document_id.get_share_link('view') or ''
                wizard.edit_link = wizard.document_id.get_share_link('edit') or ''
            else:
                wizard.view_link = ''
                wizard.edit_link = ''

    def action_add_people(self):
        """Add selected people with chosen role"""
        self.ensure_one()
        
        if not self.partner_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Selection'),
                    'message': _('Please select at least one person to share with.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        added = []
        skipped = []
        
        for partner in self.partner_ids:
            # Check if already shared
            existing = self.env['custom.document.share.line'].search([
                ('document_id', '=', self.document_id.id),
                ('partner_id', '=', partner.id)
            ], limit=1)
            
            if existing:
                skipped.append(partner.name)
                continue
            
            # Create share
            try:
                self.env['custom.document.share.line'].create({
                    'document_id': self.document_id.id,
                    'partner_id': partner.id,
                    'role': self.role,
                })
                added.append(partner.name)
            except Exception:
                skipped.append(partner.name)
        
        # Clear selection
        self.partner_ids = [(5, 0, 0)]
        
        # Build notification message
        messages = []
        if added:
            messages.append(_('✓ Added: %s') % ', '.join(added))
        if skipped:
            messages.append(_('⚠ Already shared with: %s') % ', '.join(skipped))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Share Updated'),
                'message': '\n'.join(messages) if messages else _('No changes made.'),
                'type': 'success' if added else 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_copy_view_link(self):
        """Copy view link using JavaScript client action"""
        self.ensure_one()
        
        if not self.view_link:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Link Not Available'),
                    'message': _('Please enable link sharing first (set General Access to "Anyone with link").'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_documents.copy_to_clipboard',
            'params': {
                'text': self.view_link,
                'notificationTitle': _('✓ View link copied to clipboard'),
            }
        }

    def action_copy_edit_link(self):
        """Copy edit link using JavaScript client action"""
        self.ensure_one()
        
        if self.share_access != 'link_edit':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Not Available'),
                    'message': _('Edit links require "Anyone with link – Editor" access.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        if not self.edit_link:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Link Not Available'),
                    'message': _('Unable to generate edit link.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_documents.copy_to_clipboard',
            'params': {
                'text': self.edit_link,
                'notificationTitle': _('✓ Edit link copied to clipboard'),
            }
        }