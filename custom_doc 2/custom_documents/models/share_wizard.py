# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

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

    @api.depends('document_id')
    def _compute_links(self):
        """Generate shareable links"""
        for wizard in self:
            if wizard.document_id:
                wizard.view_link = wizard.document_id.get_share_link('view')
                wizard.edit_link = wizard.document_id.get_share_link('edit')
            else:
                wizard.view_link = False
                wizard.edit_link = False

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
                'next': {'type': 'ir.actions.do_nothing'},
            }
        }

    def action_copy_view_link(self):
        """Copy view link - shows notification with link"""
        self.ensure_one()
        
        message = _(
            'View Link:\n%(link)s\n\n'
            'Anyone with this link can view the document.',
            link=self.view_link
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('📋 View Link'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }

    def action_copy_edit_link(self):
        """Copy edit link - shows notification with link"""
        self.ensure_one()
        
        if self.share_access != 'link_edit':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Not Available'),
                    'message': _('Edit links require "Anyone with link (edit)" access.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        message = _(
            'Edit Link:\n%(link)s\n\n'
            'Anyone with this link can edit the document.',
            link=self.edit_link
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('📋 Edit Link'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }

    @api.onchange('share_access')
    def _onchange_share_access(self):
        """Show warning when changing access level"""
        if not self.share_access:
            return
        
        messages = {
            'private': _('Only people you explicitly share with can access.'),
            'internal_view': _('All internal users can view this document.'),
            'internal_edit': _('All internal users can edit this document.'),
            'link_view': _('⚠️ Anyone with the link can view (no login required).'),
            'link_edit': _('⚠️ Anyone with the link can edit (no login required).'),
        }
        
        if self.share_access in messages:
            return {
                'warning': {
                    'title': _('Access Level Changed'),
                    'message': messages[self.share_access],
                }
            }