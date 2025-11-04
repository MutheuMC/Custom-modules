# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class CustomDocumentShareWizard(models.TransientModel):
    _name = 'custom.document.share.wizard'
    _description = 'Share Document Wizard'

    # ---- Target document ----
    document_id = fields.Many2one(
        'custom.document',
        string='Document',
        required=True,
        readonly=True,
    )
    document_name = fields.Char(
        string='Document Name',
        related='document_id.name',
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

    @api.depends('document_id.user_id')
    def _compute_owner_fields(self):
        for wiz in self:
            user = wiz.document_id.user_id
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
        help='Select internal users to share this document with',
    )

    # Live list bound to the real share lines on the document
    share_line_ids = fields.One2many(
        comodel_name='custom.document.share.line',
        inverse_name='document_id',
        string='People with Access',
        related='document_id.share_line_ids',
        readonly=False,   # allow inline remove in the list
    )

    # Optional badge showing current access policy if your document has this field
    share_access = fields.Selection(
        related='document_id.share_access',
        readonly=True,
    )

    internal_not_shared_count = fields.Integer(compute='_compute_internal_share_status', store=False)
    internal_fully_shared = fields.Boolean(compute='_compute_internal_share_status', store=False)

    # ---- Defaults ----
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['document_id'] = active_id
        return res

    # ---- Actions ----
    def action_share(self):
        """Create share lines for selected partners and keep the wizard open."""
        self.ensure_one()
        doc = self.document_id

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

        existing_partner_ids = set(doc.share_line_ids.mapped('partner_id').ids)
        for partner in self.partner_ids:
            if partner.id in existing_partner_ids:
                continue
            self.env['custom.document.share.line'].create({
                'document_id': doc.id,
                'partner_id': partner.id,
            })
            # (Optional) notify via chatter
            doc.message_post(
                body=_('This document has been shared with you by %s') % (doc.user_id.name,),
                subject=_('Document Shared: %s') % (doc.name,),
                message_type='notification',
                partner_ids=[partner.id],
                subtype_xmlid='mail.mt_comment',
            )

        # Clear picker; the list below refreshes because it's a related O2M
        self.partner_ids = [(5, 0, 0)]

        # Re-open the SAME wizard record to keep the modal open and refreshed
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Share "%s"') % doc.name,
        }


    def _internal_partner_ids(self):
        """Active internal users (current/doc company)."""
        self.ensure_one()
        group_user = self.env.ref('base.group_user')
        company_id = self.document_id.company_id.id or self.env.company.id
        users = self.env['res.users'].search([
            ('groups_id', 'in', group_user.id),
            ('active', '=', True),
            '|', ('company_id', '=', company_id),
                 ('company_ids', 'in', [company_id]),
        ])
        return set(users.mapped('partner_id').ids)

    @api.depends('document_id', 'document_id.share_line_ids.partner_id')
    def _compute_internal_share_status(self):
        for w in self:
            if not w.document_id:
                w.internal_not_shared_count = 0
                w.internal_fully_shared = False
                continue
            internal_set = w._internal_partner_ids()
            # don’t count the owner
            if w.owner_partner_id:
                internal_set.discard(w.owner_partner_id.id)
            already = set(w.document_id.share_line_ids.mapped('partner_id').ids)
            to_add = internal_set - already
            w.internal_not_shared_count = len(to_add)
            w.internal_fully_shared = (len(to_add) == 0)

    
    def action_share_internal(self):
        """Share with ALL internal users, skip owner/duplicates, keep wizard open."""
        self.ensure_one()
        doc = self.document_id
        internal = self._internal_partner_ids()
        if self.owner_partner_id:
            internal.discard(self.owner_partner_id.id)
        already = set(doc.share_line_ids.mapped('partner_id').ids)
        to_add = list(internal - already)
        if to_add:
            self.env['custom.document.share.line'].create(
                [{'document_id': doc.id, 'partner_id': pid} for pid in to_add]
            )
        # reopen the same wizard so UI refreshes
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Share "%s"') % doc.name,
        }