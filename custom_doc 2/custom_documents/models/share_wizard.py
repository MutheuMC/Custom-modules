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

    view_link = fields.Char(
    string='Authenticated View Link',
    compute='_compute_links',
    help='Link that requires user to be logged in'
    )

    edit_link = fields.Char(
        string='Authenticated Edit Link',
        compute='_compute_links',
        help='Link that requires user to be logged in'
    )

    # Public Share Links (no login required, token-based)
    public_view_link = fields.Char(
        string='Public View Link',
        compute='_compute_links',
        help='Public link anyone can access (no login required)'
    )

    public_edit_link = fields.Char(
        string='Public Edit Link',
        compute='_compute_links',
        help='Public link anyone can access for downloading (no login required)'
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

        # In models/share_wizard.py
    # REPLACE the _compute_links and action_copy methods:

    @api.depends('document_id', 'document_id.share_access')
    def _compute_links(self):
        """Generate both authenticated and public shareable links"""
        import logging
        _logger = logging.getLogger(__name__)
        
        for wizard in self:
            _logger.info("=" * 60)
            _logger.info("COMPUTING SHARE LINKS")
            _logger.info("=" * 60)
            
            if not wizard.document_id:
                _logger.warning("❌ No document_id")
                wizard.view_link = ''
                wizard.edit_link = ''
                wizard.public_view_link = ''
                wizard.public_edit_link = ''
                continue
            
            doc = wizard.document_id
            
            _logger.info(f"📄 Document: {doc.name} (ID: {doc.id})")
            _logger.info(f"📁 Document Type: {doc.document_type}")
            _logger.info(f"🔒 Share Access: {doc.share_access}")
            _logger.info(f"📎 Has File: {bool(doc.file)}")
            _logger.info(f"📝 File Name: {doc.file_name}")
            
            # Authenticated links (require login)
            view_link = doc.get_share_link('view')
            edit_link = doc.get_share_link('edit')
            
            _logger.info(f"🔗 View Link: {view_link or 'NONE'}")
            _logger.info(f"✏️  Edit Link: {edit_link or 'NONE'}")
            
            wizard.view_link = view_link or ''
            wizard.edit_link = edit_link or ''
            
            # Public links (no login required, token-based)
            public_view = doc.get_public_share_link('view')
            public_edit = doc.get_public_share_link('edit')
            
            _logger.info(f"🌐 Public View: {public_view or 'NONE'}")
            _logger.info(f"📥 Public Edit: {public_edit or 'NONE'}")
            
            wizard.public_view_link = public_view or ''
            wizard.public_edit_link = public_edit or ''
            
            _logger.info("=" * 60)


    def action_copy_view_link(self):
        """Copy authenticated view link (requires login)"""
        import logging
        _logger = logging.getLogger(__name__)
        
        self.ensure_one()
        
        _logger.info("🖱️ COPY VIEW LINK CLICKED")
        _logger.info(f"  view_link value: '{self.view_link}'")
        _logger.info(f"  view_link length: {len(self.view_link or '')}")
        _logger.info(f"  view_link bool: {bool(self.view_link)}")
        _logger.info(f"  document: {self.document_id.name if self.document_id else 'NO DOC'}")
        _logger.info(f"  share_access: {self.document_id.share_access if self.document_id else 'N/A'}")
        
        if not self.view_link:
            _logger.warning("❌ view_link is empty/False")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Link Not Available'),
                    'message': _(
                        'No link generated. Current access level: %s\n\n'
                        'To enable links:\n'
                        '• Set "General Access" to "Internal View" or higher\n'
                        '• Ensure document has a file uploaded'
                    ) % (self.document_id.share_access if self.document_id else 'unknown'),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        _logger.info(f"✅ Copying link: {self.view_link}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_documents.copy_to_clipboard',
            'params': {
                'text': self.view_link,
                'notificationTitle': _('✓ View link copied to clipboard'),
            }
        }


    def action_copy_edit_link(self):
        """Copy authenticated edit link (requires login)"""
        self.ensure_one()
        
        if self.share_access not in ('link_edit', 'internal_edit'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Not Available'),
                    'message': _('Edit links require "Editor" access level.'),
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


    def action_copy_public_view_link(self):
        """Copy public view link (no login required)"""
        self.ensure_one()
        
        if not self.public_view_link:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Public Link Not Available'),
                    'message': _('Set General Access to "Anyone with link – Viewer" to enable public links.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_documents.copy_to_clipboard',
            'params': {
                'text': self.public_view_link,
                'notificationTitle': _('✓ Public view link copied to clipboard'),
            }
        }


    def action_copy_public_edit_link(self):
        """Copy public edit link (no login required)"""
        self.ensure_one()
        
        if not self.public_edit_link:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Public Edit Link Not Available'),
                    'message': _('Set General Access to "Anyone with link – Editor" to enable public edit links.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_documents.copy_to_clipboard',
            'params': {
                'text': self.public_edit_link,
                'notificationTitle': _('✓ Public edit link copied to clipboard'),
            }
        }