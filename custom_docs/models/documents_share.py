# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta
import secrets, string
from odoo.exceptions import UserError

class DocumentsShare(models.Model):
    _name = 'documents.share'
    _description = 'Document Share Link'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, default='New Share')
    active = fields.Boolean(default=True, string='Active')

    access_token = fields.Char(string='Access Token', required=True,
                               default=lambda self: self._generate_access_token())
    share_type = fields.Selection([
        ('ids', 'Selected Documents'),
        ('folder', 'Entire Folder')
    ], string='Share Type', default='ids', required=True)

    document_ids = fields.Many2many('documents.document', string='Documents')
    folder_id = fields.Many2one('documents.folder', string='Folder')

    action = fields.Selection([
        ('download', 'Download'),
        ('downloadupload', 'Download and Upload')
    ], string='Action', default='download', required=True)

    date_deadline = fields.Date(string='Valid Until',
                                default=lambda self: fields.Date.today() + timedelta(days=30))

    partner_id = fields.Many2one('res.partner', string='Contact')
    email = fields.Char(string='Email')

    include_sub_folders = fields.Boolean(string='Include Sub-folders',
                                         help='Share all documents in sub-folders')
    download_limit = fields.Integer(string='Download Limit',
                                    help='Maximum number of downloads (0 = unlimited)')
    download_count = fields.Integer(string='Downloads', readonly=True, default=0)

    full_url = fields.Char(string='Share URL', compute='_compute_full_url')

    # Add search= handler here 👇
    state = fields.Selection([
        ('live', 'Live'),
        ('expired', 'Expired'),
        ('consumed', 'Consumed')
    ], string='Status', compute='_compute_state', search='_search_state')

    @api.model
    def _generate_access_token(self):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))

    @api.depends('access_token')
    def _compute_full_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for share in self:
            share.full_url = f"{base_url}/documents/share/{share.access_token}"

    @api.depends('date_deadline', 'download_limit', 'download_count', 'active')
    def _compute_state(self):
        today = fields.Date.today()
        for share in self:
            if not share.active:
                share.state = 'expired'
            elif share.date_deadline and share.date_deadline < today:
                share.state = 'expired'
            elif share.download_limit and share.download_count >= share.download_limit:
                share.state = 'consumed'
            else:
                share.state = 'live'

    # NEW: make 'state' searchable
    def _search_state(self, operator, value):
        """Translate searches on computed 'state' into an id domain."""
        if operator not in ('=', '!=', 'in', 'not in'):
            # unsupported operator for this computed selection
            return [('id', '=', 0)]

        # normalize values -> a set of target states
        if operator in ('=', '!='):
            targets = {value}
        else:  # in / not in
            targets = set(value or [])

        today = fields.Date.today()
        Share = self.env['documents.share'].sudo()

        # expired: inactive OR deadline passed
        expired_ids = set(Share.search([
            '|',
                ('active', '=', False),
                '&', ('date_deadline', '!=', False), ('date_deadline', '<', today),
        ]).ids)

        # consumed: active, has a positive limit, count >= limit, and NOT expired
        consumed_candidates = Share.search([
            ('active', '=', True),
            ('download_limit', '>', 0),
        ])
        consumed_ids = {s.id for s in consumed_candidates
                        if (s.id not in expired_ids) and (s.download_count >= s.download_limit)}

        # live: everything else
        all_ids = set(Share.search([]).ids)
        live_ids = all_ids - expired_ids - consumed_ids

        by_state = {
            'expired': expired_ids,
            'consumed': consumed_ids,
            'live':    live_ids,
        }

        wanted = set()
        for t in targets:
            wanted |= by_state.get(t, set())

        # invert if needed
        if operator in ('!=', 'not in'):
            wanted = all_ids - wanted

        return [('id', 'in', list(wanted))]

    def action_send_share(self):
        self.ensure_one()
        if not self.email and not (self.partner_id and self.partner_id.email):
            raise UserError(_('Please specify an email address.'))
        template = self.env.ref('custom_docs.email_template_document_share', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return {'type': 'ir.actions.act_window_close'}

    def action_deactivate(self):
        self.write({'active': False})

    def increment_download(self):
        self.ensure_one()
        self.download_count += 1
