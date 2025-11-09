# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError  # (kept in case you add checks later)

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
        """Link partner to user account."""
        for rec in self:
            rec.user_id = rec.partner_id.user_ids[:1].id if rec.partner_id.user_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        """Create share and notify (no roles)."""
        records = super().create(vals_list)

        for line in records:
            if not line.partner_id or not line.document_id:
                continue

            doc = line.document_id
            partner = line.partner_id

            # Add as follower (appears in "Shared with me")
            if partner.id not in doc.message_partner_ids.ids:
                doc.message_subscribe(partner_ids=[partner.id])

            # Send notification (no role mention)
            doc.message_post(
                body=_('%(doc)s has been shared with %(person)s.') % {
                    'doc': doc.name,
                    'person': partner.name,
                },
                subject=_('Document Shared'),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
                partner_ids=[partner.id],
            )

        return records

    def write(self, vals):
        """No role tracking anymore—just write."""
        return super().write(vals)

    def unlink(self):
        """Remove followers when unsharing (if no other share lines remain)."""
        partners_by_doc = {}

        for line in self:
            doc_id = line.document_id.id
            partners_by_doc.setdefault(doc_id, set()).add(line.partner_id.id)

        res = super().unlink()

        # Clean up followers
        for doc_id, partner_ids in partners_by_doc.items():
            doc = self.env['custom.document'].browse(doc_id)
            if not doc.exists():
                continue

            remaining = set(doc.share_line_ids.mapped('partner_id').ids)
            to_remove = partner_ids - remaining

            if to_remove:
                followers = doc.message_follower_ids.filtered(
                    lambda f: f.partner_id.id in to_remove
                )
                followers.unlink()

        return res

    def name_get(self):
        """Display only the person's name (roles removed)."""
        return [(rec.id, rec.partner_id.name) for rec in self]
