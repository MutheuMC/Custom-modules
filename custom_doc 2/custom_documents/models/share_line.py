# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CustomDocumentShareLine(models.Model):
    _name = 'custom.document.share.line'
    _description = 'Document Share Line - People with Access'
    _rec_name = 'partner_id'
    _order = 'create_date desc'

    document_id = fields.Many2one(
        'custom.document',
        string='Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Person',
        required=True,
        index=True
    )
     # partner_avatar = fields.Image(
    #     string='Avatar', related='partner_id.image_128', readonly=True, store=False
    # )
    # partner_name = fields.Char(
    #     string='Name', related='partner_id.display_name', readonly=True, store=False
    # )
    
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        readonly=True,
        store=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        compute='_compute_user',
        store=True,
        index=True
    )
    
    role = fields.Selection([
        ('viewer', 'Viewer'),
        ('commenter', 'Commenter'),
        ('editor', 'Editor'),
    ], string='Role', default='viewer', required=True)
    
    create_date = fields.Datetime(
        string='Shared On',
        readonly=True,
        index=True
    )

    _sql_constraints = [
        ('unique_partner_document',
         'UNIQUE(document_id, partner_id)',
         'This person already has access to this document!')
    ]

    @api.depends('partner_id')
    def _compute_user(self):
        """Link partner to user account"""
        for rec in self:
            rec.user_id = rec.partner_id.user_ids[:1].id if rec.partner_id.user_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        """Create share and notify"""
        records = super().create(vals_list)
        
        for line in records:
            if not line.partner_id or not line.document_id:
                continue
            
            doc = line.document_id
            partner = line.partner_id
            
            # Add as follower (appears in "Shared with me")
            if partner.id not in doc.message_partner_ids.ids:
                doc.message_subscribe(partner_ids=[partner.id])
            
            # Send notification
            role_name = dict(line._fields['role'].selection).get(line.role)
            doc.message_post(
                body=_('%(doc)s has been shared with %(person)s as %(role)s',
                      doc=doc.name,
                      person=partner.name,
                      role=role_name),
                subject=_('Document Shared'),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
                partner_ids=[partner.id],
            )
        
        return records

    def write(self, vals):
        """Track role changes"""
        old_roles = {rec.id: rec.role for rec in self}
        res = super().write(vals)
        
        if 'role' in vals:
            for rec in self:
                if old_roles.get(rec.id) != rec.role:
                    role_name = dict(rec._fields['role'].selection).get(rec.role)
                    rec.document_id.message_post(
                        body=_('%(person)s\'s access changed to %(role)s',
                              person=rec.partner_id.name,
                              role=role_name),
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                        partner_ids=[rec.partner_id.id],
                    )
        
        return res

    def unlink(self):
        """Remove followers when unsharing"""
        partners_by_doc = {}
        
        for line in self:
            doc_id = line.document_id.id
            if doc_id not in partners_by_doc:
                partners_by_doc[doc_id] = set()
            partners_by_doc[doc_id].add(line.partner_id.id)
        
        res = super().unlink()
        
        # Clean up followers
        for doc_id, partner_ids in partners_by_doc.items():
            doc = self.env['custom.document'].browse(doc_id)
            if not doc.exists():
                continue
            
            # Only remove if no other share lines exist
            remaining = set(doc.share_line_ids.mapped('partner_id').ids)
            to_remove = partner_ids - remaining
            
            if to_remove:
                followers = doc.message_follower_ids.filtered(
                    lambda f: f.partner_id.id in to_remove
                )
                followers.unlink()
        
        return res

    def name_get(self):
        """Display name with role"""
        result = []
        for rec in self:
            role = dict(self._fields['role'].selection).get(rec.role)
            name = f"{rec.partner_id.name} ({role})"
            result.append((rec.id, name))
        return result