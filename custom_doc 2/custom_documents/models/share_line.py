# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CustomDocumentShareLine(models.Model):
    _name = 'custom.document.share.line'
    _description = 'Document Share (People with access)'
    _rec_name = 'partner_id'

    document_id = fields.Many2one('custom.document', required=True, ondelete='cascade')
    partner_id  = fields.Many2one('res.partner', string='Person', required=True)
    user_id     = fields.Many2one('res.users', string='User', compute='_compute_user', store=True)
    role = fields.Selection([
        ('viewer', 'Viewer'),
        ('commenter', 'Commenter'),
        ('editor', 'Editor'),
    ], default='viewer', required=True)

    @api.depends('partner_id')
    def _compute_user(self):
        for rec in self:
            rec.user_id = rec.partner_id.user_ids[:1].id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # subscribe as follower so it appears under “Shared with me”
        for line in records:
            if line.partner_id and line.document_id:
                line.document_id.message_subscribe(partner_ids=[line.partner_id.id])
        return records

    def unlink(self):
        partners = self.mapped('partner_id').ids
        docs = self.mapped('document_id')
        res = super().unlink()
        # remove follower only if no other share line for that partner remains
        for d in docs:
            to_remove = set(partners) - set(d.share_line_ids.mapped('partner_id').ids)
            if to_remove:
                d.message_follower_ids.filtered(lambda f: f.partner_id.id in to_remove).unlink()
        return res
