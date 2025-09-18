import base64
import mimetypes
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CustomDocument(models.Model):
    _name = 'custom.document'
    _description = 'Custom Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

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

    # Server-side convenience flag (not stored)
    is_pdf = fields.Boolean(compute="_compute_is_pdf", store=False)
    file_kind = fields.Selection(
        [('pdf', 'PDF'), ('file', 'File'), ('url', 'URL')],
        compute='_compute_file_kind', store=True
    )

    # URL fields
    url = fields.Char('URL')

    # Organization fields
    folder_id = fields.Many2one('custom.document.folder', 'Folder', ondelete='cascade', index=True)

    # Meta fields
    description = fields.Text('Description')
    tag_ids = fields.Many2many('custom.document.tag', string='Tags')
    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    # Additional fields
    active = fields.Boolean('Active', default=True)
    color = fields.Integer('Color')
    priority = fields.Selection([('0', 'Normal'), ('1', 'High')], string='Priority', default='0')

    # Locking
    is_locked = fields.Boolean('Locked', default=False)
    locked_by = fields.Many2one('res.users', 'Locked By')

    # For viewing in same tab
    file_view_url = fields.Char('File View URL', compute='_compute_file_view_url')



    is_starred = fields.Boolean('Starred', default=False) 

    # ----------------------------
    # Computes & constraints
    # ----------------------------
    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            if rec.file:
                try:
                    rec.file_size = len(base64.b64decode(rec.file))
                except Exception:
                    rec.file_size = 0
            else:
                rec.file_size = 0

    @api.depends('document_type', 'file')
    def _compute_file_view_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.document_type == 'file' and rec.file:
                rec.file_view_url = f"{base_url}/web/content/custom.document/{rec.id}/file/{rec.file_name or 'document'}"
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
        """Robust PDF detection that also works when Binary is read with bin_size=True."""
        for rec in self:
            is_pdf = False
            if rec.document_type == 'file':
                name = (rec.file_name or '').lower()
                mt = (rec.mimetype or '').lower()
                if 'pdf' in mt or name.endswith('.pdf'):
                    is_pdf = True
                else:
                    # Binary may be a size string if read with bin_size=True.
                    data = rec.file
                    needs_fetch = not data or not isinstance(data, str) or (' ' in data) or data.endswith('B')
                    if needs_fetch:
                        data = rec.with_context(bin_size=False).file
                    if data and isinstance(data, str):
                        try:
                            head = base64.b64decode(data)[:5]
                            is_pdf = (head == b'%PDF-')
                        except Exception:
                            is_pdf = False
            rec.is_pdf = is_pdf


    @api.depends('document_type', 'mimetype', 'file_name', 'file')
    def _compute_file_kind(self):
        for rec in self:
            # default by type
            kind = 'url' if rec.document_type == 'url' else 'file'
            if rec.document_type == 'file':
                mt = (rec.mimetype or '').lower()
                name = (rec.file_name or '').lower()
                if 'pdf' in mt or name.endswith('.pdf'):
                    kind = 'pdf'
                else:
                    # last-resort sniff; handles when mimetype/filename are missing
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

    # ----------------------------
    # Create / write
    # ----------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_type') == 'url' and vals.get('url') and not vals.get('name'):
                vals['name'] = vals['url'].split('/')[-1] or _('URL Document')
            elif vals.get('file_name') and not vals.get('name'):
                vals['name'] = vals['file_name']

            # Detect MIME type for files
            if vals.get('file') and not vals.get('mimetype'):
                if vals.get('file_name'):
                    mt, _enc = mimetypes.guess_type(vals['file_name'])
                    if mt:
                        vals['mimetype'] = mt
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('file') and not vals.get('mimetype'):
            file_name = vals.get('file_name') or self.file_name
            if file_name:
                mt, _enc = mimetypes.guess_type(file_name)
                if mt:
                    vals['mimetype'] = mt
        return super().write(vals)

    # ----------------------------
    # Actions
    # ----------------------------
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
        """Return the ir.attachment that stores this record's `file` field.
        If not found (rare), create a normal attachment for the viewer."""
        self.ensure_one()
        Att = self.env['ir.attachment']
        # When Binary has attachment=True, Odoo stores it as an attachment with res_field
        att = Att.search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'file'),
        ], limit=1)
        if att:
            return att
        # Fallback (if not stored with res_field for any reason)
        return Att.create({
            'name': self.file_name or (self.name + '.pdf'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': self.mimetype or 'application/pdf',
            'datas': self.file,  # base64
        })

    # ----------------------------
    # Actions
    # ----------------------------
    def action_view_file(self):
        """Open PDF in a modal (same tab) using a transient wizard instance."""
        self.ensure_one()
        if self.document_type != 'file' or not self.file:
            return False

        # Decide if it's a PDF; otherwise fallback to download
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

        # CREATE the wizard record first so pdf_viewer has a res_id to stream from
        wiz = self.env['custom.document.preview.wizard'].sudo().create({
            'document_id': self.id,   # NEW

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
            'target': 'new',              # modal overlay, same tab
            'context': {'dialog_size': 'large'},
        }
    


    def _ensure_single(self, label=_("this action")):
        if len(self) != 1:
            raise UserError(_("Please select exactly one document for %s.") % label)

    # ---------- Actions menu entries (for list view) ----------
    def action_menu_download(self):
        self._ensure_single(_("download"))
        return self.action_download()

    def action_menu_share(self):
        self._ensure_single(_("share"))
        base = f"/web/content/custom.document/{self.id}/file/{self.file_name or 'file'}"
        raise UserError(_("Share link:\n%s") % base)

    def action_menu_duplicate(self):
        # duplicate all selected
        new_ids = []
        for d in self:
            vals = {
                'name': (d.name or '') + ' (copy)',
                'document_type': d.document_type,
                'file': d.with_context(bin_size=False).file,
                'file_name': d.file_name,
                'mimetype': d.mimetype,
                'url': d.url,
                'folder_id': d.folder_id.id,
                'tag_ids': [(6, 0, d.tag_ids.ids)],
            }
            new_ids.append(self.sudo().create(vals).id)
        if len(new_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'custom.document',
                'view_mode': 'form',
                'res_id': new_ids[0],
                'target': 'current',
            }
        # reopen list filtered on the new copies
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', new_ids)],
            'target': 'current',
        }

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
        # show all links for selected docs
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

    # def action_menu_split_pdf(self):
    #     self._ensure_single(_("split PDF"))
    #     raise UserError(_("Split PDF: not implemented yet."))

    # def action_menu_sign(self):
    #     self._ensure_single(_("sign"))
    #     raise UserError(_("Sign: integrate with the Sign app if installed."))


