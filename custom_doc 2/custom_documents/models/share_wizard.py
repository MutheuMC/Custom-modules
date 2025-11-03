# models/share_wizard.py - SIMPLIFIED VERSION

from odoo import models, fields, api, _

class CustomDocumentShareWizard(models.TransientModel):
    _name = 'custom.document.share.wizard'
    _description = 'Share Document Wizard'

    document_id = fields.Many2one(
        'custom.document',
        required=True,
        readonly=True
    )
    
    # Add people (no role needed)
    partner_ids = fields.Many2many(
        'res.partner',
        string='Share with',
        domain=[('user_ids', '!=', False)],  # Only partners with user accounts
        help='Select internal users to share this document with'
    )
    
    # Current shares (inline editable)
    share_line_ids = fields.One2many(
        related='document_id.share_line_ids',
        readonly=False
    )
    
    # Sharing status
    share_access = fields.Selection(
        related='document_id.share_access',
        readonly=False
    )
    
    def action_share(self):
        """Share document with selected users and notify them"""
        self.ensure_one()
        
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
        
        added = []
        existing = []
        
        for partner in self.partner_ids:
            # Check if already shared
            if partner in self.document_id.share_line_ids.mapped('partner_id'):
                existing.append(partner.name)
                continue
            
            # Create share
            self.env['custom.document.share.line'].create({
                'document_id': self.document_id.id,
                'partner_id': partner.id,
            })
            added.append(partner.name)
            
            # Send notification
            self.document_id.message_post(
                body=_('This document has been shared with you by %s', 
                      self.document_id.user_id.name),
                subject=_('Document Shared: %s', self.document_id.name),
                message_type='notification',
                partner_ids=[partner.id],
                subtype_xmlid='mail.mt_comment',
            )
        
        # Update sharing status
        if self.document_id.share_line_ids and self.document_id.share_access == 'private':
            self.document_id.share_access = 'internal'
        
        # Build notification
        messages = []
        if added:
            messages.append(_('✓ Shared with: %s') % ', '.join(added))
        if existing:
            messages.append(_('ℹ Already shared with: %s') % ', '.join(existing))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Document Shared'),
                'message': '\n'.join(messages),
                'type': 'success',
                'sticky': False,
            }
        }

