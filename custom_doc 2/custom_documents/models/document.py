# -*- coding: utf-8 -*-
import base64
import mimetypes
import re
from datetime import timedelta
from secrets import token_urlsafe

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CustomDocument(models.Model):
    _name = 'custom.document'
    _description = 'Custom Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    name = fields.Char('Document Name', required=True, tracking=True)

    document_type = fields.Selection(
        [('file', 'File'), ('url', 'URL Link')],
        string='Type', default='file', required=True
    )

    # File fields
    file = fields.Binary('File', attachment=True)
    file_name = fields.Char('File Name')
    file_size = fields.Integer('File Size', compute='_compute_file_size')
    mimetype = fields.Char('MIME Type')

    # Convenience (server-side)
    is_pdf = fields.Boolean(compute="_compute_is_pdf", store=False)
    file_kind = fields.Selection(
        [('pdf', 'PDF'), ('file', 'File'), ('url', 'URL')],
        compute='_compute_file_kind', store=True
    )

    # URL
    url = fields.Char('URL')

    # Organization
    folder_id = fields.Many2one(
        'custom.document.folder', 'Folder',
        ondelete='cascade', index=True,
        domain="[('is_virtual', '=', False)]"
    )

    # Kept for compatibility (used only if you reference it elsewhere)
    computed_folder_id = fields.Many2one(
        'custom.document.folder', string='Display Folder',
        compute='_compute_display_folder', search='_search_display_folder',
        store=False
    )

    # Meta
    description = fields.Text('Description')
    tag_ids = fields.Many2many('custom.document.tag', string='Tags')
    user_id = fields.Many2one('res.users', 'Owner',
                              default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)

    # Other
    active = fields.Boolean('Active', default=True)
    color = fields.Integer('Color')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'High')],
        string='Priority', default='0'
    )

    # Locking
    is_locked = fields.Boolean('Locked', default=False)
    locked_by = fields.Many2one('res.users', 'Locked By')

    # File view (same tab)
    file_view_url = fields.Char('File View URL', compute='_compute_file_view_url')

    # UX flags
    is_starred = fields.Boolean('Starred', default=False)

    # -------------------------------------------------------------------------
    # SHARE FIELDS - UPDATED FOR GOOGLE DOCS-STYLE SHARING
    # -------------------------------------------------------------------------
    share_access = fields.Selection([
        ('private', 'Restricted'),
        ('internal_view', 'Your organization – Viewer'),
        ('internal_edit', 'Your organization – Editor'),
        ('link_view', 'Anyone with link – Viewer'),
        ('link_edit', 'Anyone with link – Editor'),
    ], string='General Access', default='private', tracking=True)

    share_line_ids = fields.One2many(
        'custom.document.share.line',
        'document_id',
        string='People with Access',
        copy=False,
    )
    share_token_view = fields.Char(
        'View token', 
        copy=False, 
        default=lambda self: token_urlsafe(32)
    )
    share_token_edit = fields.Char(
        'Edit token', 
        copy=False, 
        default=lambda self: token_urlsafe(32)
    )
    
    # Computed fields for share status
    is_shared = fields.Boolean(
        string='Is Shared',
        compute='_compute_is_shared',
        store=True
    )
    shared_with_count = fields.Integer(
        string='Shared With',
        compute='_compute_shared_with_count',
        store=True
    )

    # Virtual folders (computed membership)
    virtual_folder_ids = fields.Many2many(
        'custom.document.folder', compute='_compute_virtual_folder_ids',
        string='Virtual Folders', store=False
    )

    # Search-only helpers for SearchPanel filters
    is_recent = fields.Boolean(string='Recent', store=False, search='_search_is_recent')
    is_shared_with_me = fields.Boolean(string='Shared with Me', store=False, search='_search_shared_with_me')

    # -------------------------------------------------------------------------
    # Computes & Constraints
    # -------------------------------------------------------------------------
    @api.depends('file')
    def _compute_file_size(self):
        """Compute real byte size even if binary is loaded with bin_size=True."""
        for rec in self:
            size = 0
            data = rec.file
            # If it's a human-readable size (e.g., '10.5KB'), fetch full binary
            needs_fetch = (not data or not isinstance(data, str)
                           or (' ' in data) or (isinstance(data, str) and data.endswith('B')))
            if needs_fetch:
                data = rec.with_context(bin_size=False).file
            if data and isinstance(data, str):
                try:
                    size = len(base64.b64decode(data))
                except Exception:
                    size = 0
            rec.file_size = size

    @api.depends('document_type', 'file')
    def _compute_file_view_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.document_type == 'file' and rec.file:
                fname = rec.file_name or 'document'
                rec.file_view_url = f"{base_url}/web/content/custom.document/{rec.id}/file/{fname}"
            else:
                rec.file_view_url = False

    @api.constrains('document_type', 'file', 'url')
    def _check_document_data(self):
        for rec in self:
            if rec.document_type == 'file' and not rec.file:
                raise ValidationError(_('Please upload a file.'))
            if rec.document_type == 'url' and not rec.url:
                raise ValidationError(_('Please provide a URL.'))

    @api.depends('document_type', 'mimetype', 'file_name', 'file')
    def _compute_is_pdf(self):
        """Robust PDF sniffing (works even if bin_size=True)."""
        for rec in self:
            is_pdf = False
            if rec.document_type == 'file':
                name = (rec.file_name or '').lower()
                mt = (rec.mimetype or '').lower()
                if 'pdf' in mt or name.endswith('.pdf'):
                    is_pdf = True
                else:
                    data = rec.file
                    needs_fetch = (not data or not isinstance(data, str)
                                   or (' ' in data) or data.endswith('B'))
                    if needs_fetch:
                        data = rec.with_context(bin_size=False).file
                    if data and isinstance(data, str):
                        try:
                            is_pdf = (base64.b64decode(data)[:5] == b'%PDF-')
                        except Exception:
                            is_pdf = False
            rec.is_pdf = is_pdf

    @api.depends('document_type', 'mimetype', 'file_name', 'file')
    def _compute_file_kind(self):
        for rec in self:
            kind = 'url' if rec.document_type == 'url' else 'file'
            if rec.document_type == 'file':
                mt = (rec.mimetype or '').lower()
                name = (rec.file_name or '').lower()
                if 'pdf' in mt or name.endswith('.pdf'):
                    kind = 'pdf'
                else:
                    data = rec.file
                    needs_fetch = (not data or not isinstance(data, str)
                                   or (' ' in data) or data.endswith('B'))
                    if needs_fetch:
                        data = rec.with_context(bin_size=False).file
                    if data and isinstance(data, str):
                        try:
                            if base64.b64decode(data)[:5] == b'%PDF-':
                                kind = 'pdf'
                        except Exception:
                            pass
            rec.file_kind = kind

    def _compute_display_folder(self):
        """Compatibility shim: mirror folder_id."""
        for doc in self:
            doc.computed_folder_id = doc.folder_id

    def _search_display_folder(self, operator, value):
        """Enable searching by a 'virtual' folder value (if ever used)."""
        if not value:
            return [('folder_id', operator, value)]

        if isinstance(value, list):
            value = value[-1] if value else False

        if not value:
            return [('folder_id', operator, value)]

        folder = self.env['custom.document.folder'].sudo().browse(value)
        if not folder.exists():
            return [('id', '=', False)]

        if folder.is_virtual:
            # Delegate to folder's virtual domain
            return folder._get_virtual_folder_domain(folder.virtual_type)
        # Real folder: include subfolders
        return [('folder_id', 'child_of', value)]

    # -------------------------------------------------------------------------
    # SHARE COMPUTED FIELDS
    # -------------------------------------------------------------------------
    @api.depends('share_line_ids', 'share_access')
    def _compute_is_shared(self):
        for doc in self:
            doc.is_shared = bool(doc.share_line_ids) or doc.share_access != 'private'

    @api.depends('share_line_ids')
    def _compute_shared_with_count(self):
        for doc in self:
            doc.shared_with_count = len(doc.share_line_ids)

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_type') == 'url' and vals.get('url') and not vals.get('name'):
                vals['name'] = vals['url'].split('/')[-1] or _('URL Document')
            elif vals.get('file_name') and not vals.get('name'):
                vals['name'] = vals['file_name']

            # Guess mimetype for uploaded files
            if vals.get('file') and not vals.get('mimetype'):
                fname = vals.get('file_name')
                if fname:
                    mt, _enc = mimetypes.guess_type(fname)
                    if mt:
                        vals['mimetype'] = mt
        return super().create(vals_list)

    def write(self, vals):
        """Override write to check permissions"""
        for rec in self:
            # Allow harmless flags from viewers (stars, following)
            harmless = {'is_starred', 'message_follower_ids'}
            if set(vals) - harmless and not rec._is_editor():
                raise UserError(_('You do not have permission to edit this document.'))
        
        if vals.get('file') and not vals.get('mimetype'):
            file_name = vals.get('file_name') or self.file_name
            if file_name:
                mt, _enc = mimetypes.guess_type(file_name)
                if mt:
                    vals['mimetype'] = mt
        return super().write(vals)

    # -------------------------------------------------------------------------
    # SHARE METHODS
    # -------------------------------------------------------------------------
    def _generate_token(self):
        """Generate a secure random token"""
        return token_urlsafe(32)

    def _ensure_token(self, kind='view'):
        """Ensure token exists and return it"""
        self.ensure_one()
        field = 'share_token_view' if kind == 'view' else 'share_token_edit'
        token = self[field]
        if not token:
            token = self._generate_token()
            self.write({field: token})
        return token

    def get_share_link(self, mode='view'):
        """Return a token-based URL for public access."""
        self.ensure_one()
        if mode == 'edit':
            if self.share_access != 'link_edit':
                return False
            token = self._ensure_token('edit')
        else:
            if self.share_access not in ('link_view', 'link_edit'):
                return False
            token = self._ensure_token('view')

        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        path = f"/documents/s/{token}"
        return f"{base}{path}" if base else path   # relative URL works locally and behind proxies



    def regenerate_share_token(self):
        """Regenerate share tokens (invalidates old links)"""
        self.ensure_one()
        self.write({
            'share_token_view': self._generate_token(),
            'share_token_edit': self._generate_token(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tokens Regenerated'),
                'message': _('All previous share links have been invalidated.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_open_share_wizard(self):
        """Open share wizard"""
        self.ensure_one()
        return {
            'name': _('Share "%s"', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
            }
        }

    def _is_editor(self):
        """Check if current user can edit this document"""
        self.ensure_one()
        u = self.env.user
        
        # Owner can always edit
        if self.user_id.id == u.id:
            return True
        
        # Internal edit access
        if self.share_access == 'internal_edit':
            return True
        
        # Check share lines
        return bool(
            self.share_line_ids.filtered(
                lambda l: l.user_id.id == u.id and l.role == 'editor'
            )
        )

    def _can_view(self):
        """Check if current user can view this document"""
        self.ensure_one()
        u = self.env.user
        
        # Owner can always view
        if self.user_id.id == u.id:
            return True
        
        # Internal users
        if self.share_access in ('internal_view', 'internal_edit'):
            return True
        
        # Check share lines (any role can view)
        return bool(
            self.share_line_ids.filtered(lambda l: l.user_id.id == u.id)
        )

    # def check_access(self, partner_id=None, token=None, access_type='read'):
    #     """Check if user/partner has access to document"""
    #     self.ensure_one()
        
    #     # System/admin always has access
    #     if self.env.su:
    #         return True
        
    #     # Check if current user is owner
    #     if self.create_uid == self.env.user:
    #         return True
        
    #     # Check token-based access
    #     if token:
    #         if token == self.share_token_view and self.share_access in ('link_view', 'link_edit'):
    #             if access_type == 'read':
    #                 return True
    #         if token == self.share_token_edit and self.share_access == 'link_edit':
    #             if access_type in ('read', 'write'):
    #                 return True
        
    #     # Check partner-specific access
    #     if partner_id or self.env.user.partner_id:
    #         partner = partner_id or self.env.user.partner_id.id
    #         share_line = self.share_line_ids.filtered(
    #             lambda l: l.partner_id.id == partner
    #         )
            
    #         if share_line:
    #             if access_type == 'read':
    #                 return True
    #             if access_type == 'write' and share_line.role == 'editor':
    #                 return True
    #             if access_type == 'comment' and share_line.role in ('commenter', 'editor'):
    #                 return True
        
    #     return False
    

    # --- REPLACE your current check_access with these two methods ---

    def has_share_access(self, partner_id=None, token=None, access_type='read'):
        """Custom share logic (token/partner-based). Safe if called on empty set."""
        if not self:
            return False
        self.ensure_one()

        # System/admin always has access
        if self.env.su:
            return True

        # Owner can always view/edit (use your original rule – keep as you had)
        if self.create_uid == self.env.user:
            return True

        # Token-based access
        if token:
            if token == self.share_token_view and self.share_access in ('link_view', 'link_edit'):
                if access_type == 'read':
                    return True
            if token == self.share_token_edit and self.share_access == 'link_edit':
                if access_type in ('read', 'write'):
                    return True

        # Partner-specific access
        partner = partner_id or (self.env.user.partner_id.id if self.env.user.partner_id else False)
        if partner:
            line = self.share_line_ids.filtered(lambda l: l.partner_id.id == partner)
            if line:
                if access_type == 'read':
                    return True
                if access_type == 'comment' and line.role in ('commenter', 'editor'):
                    return True
                if access_type == 'write' and line.role == 'editor':
                    return True

        return False


    def check_access(self, *args, **kwargs):
        return super().check_access(*args, **kwargs)



    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_download(self):
        self.ensure_one()
        if self.document_type == 'file':
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{self._name}/{self.id}/file/{self.file_name or ''}?download=true",
                'target': 'self',
            }
        if self.document_type == 'url':
            return {'type': 'ir.actions.act_url', 'url': self.url, 'target': 'new'}

    def action_debug_flags(self):
        self.ensure_one()
        msg = (
            "Debug values\n"
            f"- document_type: {self.document_type}\n"
            f"- file_name: {self.file_name}\n"
            f"- mimetype: {self.mimetype}\n"
            f"- is_pdf (server): {self.is_pdf}\n"
            f"- has file data: {bool(self.file)}"
        )
        raise UserError(msg)

    def action_lock(self):
        self.ensure_one()
        if self.is_locked and self.locked_by and self.locked_by != self.env.user:
            raise UserError(_('This document is locked by %s') % self.locked_by.name)
        self.write({
            'is_locked': not self.is_locked,
            'locked_by': self.env.user.id if not self.is_locked else False,
        })

    def action_toggle_star(self):
        for rec in self:
            rec.is_starred = not rec.is_starred
        return False

    def _get_or_create_file_attachment(self):
        """Return the ir.attachment backing this record's `file` field."""
        self.ensure_one()
        Att = self.env['ir.attachment']
        att = Att.search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'file'),
        ], limit=1)
        if att:
            return att
        return Att.create({
            'name': self.file_name or (self.name + '.pdf'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': self.mimetype or 'application/pdf',
            'datas': self.file,
        })

    def action_view_file(self):
        """Open PDF in a modal via a transient wizard, else download."""
        self.ensure_one()
        if self.document_type != 'file' or not self.file:
            return False

        # Detect PDF quickly
        is_pdf_like = False
        if (self.mimetype or '').lower().find('pdf') != -1:
            is_pdf_like = True
        elif (self.file_name or '').lower().endswith('.pdf'):
            is_pdf_like = True
        else:
            try:
                blob = self.with_context(bin_size=False).file
                is_pdf_like = (base64.b64decode(blob)[:5] == b'%PDF-')
            except Exception:
                is_pdf_like = False

        if not is_pdf_like:
            return self.action_download()

        wiz = self.env['custom.document.preview.wizard'].sudo().create({
            'document_id': self.id,
            'data': self.with_context(bin_size=False).file,
            'data_fname': self.file_name or (self.name + '.pdf'),
            'mimetype': self.mimetype or 'application/pdf',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Preview'),
            'res_model': 'custom.document.preview.wizard',
            'res_id': wiz.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'xl'},
        }

    # ---------- List-view action helpers ----------
    def _ensure_single(self, label=_("this action")):
        if len(self) != 1:
            raise UserError(_("Please select exactly one document for %s.") % label)

    def _make_copy_name(self, base_name: str) -> str:
        stem = base_name or _("Untitled")
        like = f"{stem} (copy%"
        rows = self.search_read([('name', 'ilike', like)], ['name'], limit=5000)
        used = set()
        for r in rows:
            m = re.match(rf"^{re.escape(stem)}\s+\(copy(?:\s+(\d+))?\)$", r['name'], flags=re.I)
            if m:
                used.add(int(m.group(1) or 1))
        if 1 not in used:
            return f"{stem} (copy)"
        n = 2
        while n in used:
            n += 1
        return f"{stem} (copy {n})"

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.setdefault('name', self._make_copy_name(self.name))
        default.setdefault('is_locked', False)
        default.setdefault('locked_by', False)
        return super().copy(default)

    def action_menu_download(self):
        self._ensure_single(_("download"))
        return self.action_download()

    def action_menu_share(self):
        self._ensure_single(_("share"))
        return self.action_open_share_wizard()

    def action_menu_move_to_trash(self):
        self.sudo().write({'active': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_menu_lock_toggle(self):
        for d in self:
            d.sudo().action_lock()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_menu_create_shortcut(self):
        new_ids = []
        for d in self:
            url = f"/web/content/custom.document/{d.id}/file/{d.file_name or 'file'}"
            new_ids.append(self.env['custom.document'].sudo().create({
                'name': f"Shortcut to {d.name}",
                'document_type': 'url',
                'url': url,
                'folder_id': d.folder_id.id,
                'tag_ids': [(6, 0, d.tag_ids.ids)],
            }).id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', new_ids)],
            'target': 'current',
        }

    def action_menu_manage_versions(self):
        self._ensure_single(_("manage versions"))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Versions'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('res_model', '=', 'custom.document'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'custom.document', 'default_res_id': self.id},
        }

    def action_menu_copy_links(self):
        lines = []
        for d in self:
            base = f"/web/content/custom.document/{d.id}/file/{d.file_name or 'file'}"
            lines.append(f"{d.name}: {base}")
        if not lines:
            return False
        raise UserError(_("Links:\n%s") % ("\n".join(lines)))

    def action_menu_rename(self):
        self._ensure_single(_("rename"))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rename'),
            'res_model': 'custom.document.rename.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id, 'default_new_name': self.name},
        }

    def action_menu_info_tags(self):
        self._ensure_single(_("edit properties"))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Info & tags'),
            'res_model': 'custom.document.properties.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_name': self.name,
                'default_tag_ids': [(6, 0, self.tag_ids.ids)],
                'default_folder_id': self.folder_id.id,
            },
        }

    # -------------------------------------------------------------------------
    # Module init: ensure seed folders
    # -------------------------------------------------------------------------
    @api.model
    def init(self):
        """Initialize the folder structure on module installation."""
        super().init()
        company = self.env.company
        Folder = self.env['custom.document.folder'].sudo()
        Folder._get_company_root(company)
        Folder._ensure_default_company_children(company)
        if 'hr.employee' in self.env:
            employees = self.env['hr.employee'].search([('company_id', '=', company.id)])
            for emp in employees:
                Folder._ensure_employee_folder(emp)

    # -------------------------------------------------------------------------
    # Virtual folder membership + Search helpers
    # -------------------------------------------------------------------------
    @api.depends('user_id', 'write_date', 'active', 'message_partner_ids', 'share_line_ids', 'share_access')
    def _compute_virtual_folder_ids(self):
        """Compute which virtual folders this document belongs to."""
        VirtualFolder = self.env['custom.document.folder'].sudo()

        my_drive_folder = VirtualFolder.search([('virtual_type', '=', 'my_drive')], limit=1)
        shared_folder = VirtualFolder.search([('virtual_type', '=', 'shared')], limit=1)
        recent_folder = VirtualFolder.search([('virtual_type', '=', 'recent')], limit=1)
        trash_folder = VirtualFolder.search([('virtual_type', '=', 'trash')], limit=1)

        uid = self.env.uid
        partner_id = self.env.user.partner_id.id
        seven_days_ago = fields.Datetime.now() - timedelta(days=7)

        for doc in self:
            vf = []
            
            # My Drive: all documents I own (active only)
            if doc.user_id.id == uid and doc.active and my_drive_folder:
                vf.append(my_drive_folder.id)
            
            # Shared with Me: (via lines or internal) but not owner (active only)
            is_shared_internally = doc.share_access in ('internal_view', 'internal_edit')
            is_shared_directly = uid in doc.share_line_ids.user_id.ids
            
            if (is_shared_internally or is_shared_directly) and (doc.user_id.id != uid) and doc.active and shared_folder:
                vf.append(shared_folder.id)
            
            # Recent: modified in last 7 days (active only)
            if (doc.write_date and doc.write_date >= seven_days_ago) and doc.active and recent_folder:
                vf.append(recent_folder.id)
            
            # Trash: inactive documents
            if not doc.active and trash_folder:
                vf.append(trash_folder.id)
            
            doc.virtual_folder_ids = [(6, 0, vf)]

    def _search_is_recent(self, operator, value):
        """True if write_date is within the last 7 days (active only)."""
        if operator not in ('=', '=='):
            return []
        seven_days_ago = fields.Datetime.now() - timedelta(days=7)
        if value:
            return [('write_date', '>=', seven_days_ago), ('active', '=', True)]
        return ['|', ('write_date', '=', False), ('write_date', '<', seven_days_ago)]

    def _search_shared_with_me(self, operator, value):
        """True if current user is shared (directly or internal) but not the owner (active)."""
        if operator not in ('=', '=='):
            return []
        uid = self.env.uid
        
        # This is the domain for "Shared with me"
        shared_domain = [
            '|',
                ('share_line_ids.user_id', '=', uid),
                ('share_access', 'in', ['internal_view', 'internal_edit']),
            ('user_id', '!=', uid),
            ('active', '=', True)
        ]
        
        if value:
            return shared_domain
        else:
            # Return the negation of the domain
            return ['!'] + shared_domain