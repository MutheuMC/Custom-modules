# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
import base64
import hashlib
import mimetypes

class DocumentsDocument(models.Model):
    _name = 'documents.document'
    _description = 'Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    # Basic fields
    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(default=True, string='Active')
    type = fields.Selection([
        ('empty', 'File Request'),
        ('binary', 'File'),
        ('url', 'URL')
    ], string='Type', required=True, default='binary')

    # File fields
    datas = fields.Binary(string='File Content', attachment=True)
    file_size = fields.Integer(string='File Size', readonly=True)
    checksum = fields.Char(string='Checksum', readonly=True)
    mimetype = fields.Char(string='Mime Type', readonly=True)
    url = fields.Char(string='URL')

    # Organization fields
    folder_id = fields.Many2one('documents.folder', string='Folder',
                                required=True, ondelete='cascade', tracking=True)
    tag_ids = fields.Many2many('documents.tag', string='Tags')
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    owner_id = fields.Many2one('res.users', string='Owner',
                               default=lambda self: self.env.user, tracking=True)

    # Request fields
    request_partner_id = fields.Many2one('res.partner', string='Requested from')
    request_date = fields.Date(string='Request Date')
    request_deadline = fields.Date(string='Request Deadline')
    request_message = fields.Text(string='Request Message')

    # Computed fields
    is_locked = fields.Boolean(string='Locked', default=False)
    locked_by = fields.Many2one('res.users', string='Locked by')

    # IMPORTANT: make it searchable via search=; don't depend on 'id'
    is_shared = fields.Boolean(
        string='Shared',
        compute='_compute_is_shared',
        search='_search_is_shared'
    )

    available_rule_ids = fields.Many2many(
        'documents.workflow.rule',
        compute='_compute_available_rules'
    )

    # Related fields
    company_id = fields.Many2one('res.company', string='Company',
                                 related='folder_id.company_id', store=True)
    

       # Visual field
    color = fields.Integer(string='Color Index', default=0)

    @api.depends('folder_id', 'tag_ids')
    def _compute_available_rules(self):
        for document in self:
            domain = [
                ('folder_id', 'parent_of', document.folder_id.id),
                '|',
                ('condition_type', '=', 'no_condition'),
                '&',
                ('condition_type', '=', 'tag'),
                ('required_tag_ids', 'in', document.tag_ids.ids)
            ]
            document.available_rule_ids = self.env['documents.workflow.rule'].search(domain)

    # No @api.depends — it derives from other models; we compute on read
    def _compute_is_shared(self):
        Share = self.env['documents.share'].sudo()
        today = fields.Date.today()

        # live shares (deadline in future or no deadline)
        shares = Share.search([
            ('document_ids', 'in', self.ids),
            '|', ('date_deadline', '>=', today),
                 ('date_deadline', '=', False),
        ])
        shared_doc_ids = set(shares.mapped('document_ids').ids)

        # public links via ir.attachment.access_token
        attach_doc_ids = set(
            self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'documents.document'),
                ('res_id', 'in', self.ids),
                ('access_token', '!=', False),
            ]).mapped('res_id')
        )

        for rec in self:
            rec.is_shared = (rec.id in shared_doc_ids) or (rec.id in attach_doc_ids)

    def _search_is_shared(self, operator, value):
        truthy = bool(value)
        if operator in ('!=', '<>'):
            truthy = not truthy

        today = fields.Date.today()
        Share = self.env['documents.share'].sudo()

        shared_ids = set(Share.search([
            '|', ('date_deadline', '>=', today),
                 ('date_deadline', '=', False),
        ]).mapped('document_ids').ids)

        attach_ids = set(self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'documents.document'),
            ('access_token', '!=', False),
        ]).mapped('res_id'))

        ids = list(shared_ids | attach_ids)
        return [('id', 'in' if truthy else 'not in', ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('datas'):
                vals['checksum'] = self._get_checksum(vals['datas'])
                vals['file_size'] = len(base64.b64decode(vals['datas']))
                if not vals.get('mimetype'):
                    vals['mimetype'] = self._get_mimetype(vals.get('name', ''))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('datas'):
            vals['checksum'] = self._get_checksum(vals['datas'])
            vals['file_size'] = len(base64.b64decode(vals['datas']))
            if not vals.get('mimetype'):
                vals['mimetype'] = self._get_mimetype(vals.get('name', self.name))
        return super().write(vals)

    def _get_checksum(self, datas):
        return hashlib.sha1(base64.b64decode(datas)).hexdigest()

    def _get_mimetype(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    # Actions
    def action_lock(self):
        self.ensure_one()
        if self.is_locked:
            raise UserError(_('This document is already locked.'))
        self.write({'is_locked': True, 'locked_by': self.env.user.id})

    def action_unlock(self):
        self.ensure_one()
        if not self.is_locked:
            raise UserError(_('This document is not locked.'))
        if self.locked_by != self.env.user and not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only the user who locked the document can unlock it.'))
        self.write({'is_locked': False, 'locked_by': False})

    def action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.id,
            'target': 'self',
        }

    def action_share(self):
        self.ensure_one()
        return {
            'name': _('Share Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'documents.share',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_ids': [(6, 0, self.ids)],
                'default_folder_id': self.folder_id.id,
            }
        }

    def action_archive(self):
        return self.write({'active': False})

    def action_unarchive(self):
        return self.write({'active': True})

    def apply_actions(self):
        self.ensure_one()
        for rule in self.available_rule_ids:
            rule.apply_actions(self)
