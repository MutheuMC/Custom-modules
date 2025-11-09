from odoo import models, fields, _, api
from odoo.exceptions import UserError


class CustomDocumentPreviewWizard(models.TransientModel):
    _name = 'custom.document.preview.wizard'
    _description = 'Preview Document Wizard'

    # link back to the original record
    document_id = fields.Many2one('custom.document', string='Document', readonly=True)

    # data for the viewer
    data = fields.Binary(string='File', readonly=True)
    data_fname = fields.Char(string='File Name', readonly=True)
    mimetype = fields.Char(string='MIME Type', readonly=True)

    # ----------------------------
    # Helpers
    # ----------------------------
    def _content_url(self, download=False):
        self.ensure_one()
        base = f"/web/content/{self._name}/{self.id}/data/{self.data_fname or 'file'}"
        return f"{base}?download=true" if download else base

    def _doc(self):
        self.ensure_one()
        if not self.document_id:
            raise UserError(_("No document found."))
        return self.document_id.sudo()

    # ----------------------------
    # Header buttons (Download / Share)
    # ----------------------------
    def action_download(self):
        self.ensure_one()
        if not self.data:
            raise UserError(_("No file to download."))
        return {'type': 'ir.actions.act_url', 'url': self._content_url(True), 'target': 'self'}

    def action_copy_link(self):
        self.ensure_one()
        raise UserError(_("Share link:\n%s") % self._content_url(False))

    # ----------------------------
    # Actions (called from the dropdown items)
    # ----------------------------
    def action_duplicate_menu(self):
        d = self._doc()
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
        new = self.env['custom.document'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'form',
            'res_id': new.id,
            'target': 'current',
        }

    def action_move_to_trash_menu(self):
        d = self._doc()
        d.write({'active': False})
        return {'type': 'ir.actions.act_window_close'}

    def action_rename_menu(self):
        d = self._doc()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rename'),
            'res_model': 'custom.document.rename.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': d.id, 'default_new_name': d.name},
        }

    def action_info_tags_menu(self):
        d = self._doc()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Info & tags'),
            'res_model': 'custom.document.properties.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': d.id,
                'default_name': d.name,
                'default_tag_ids': [(6, 0, d.tag_ids.ids)],
                'default_folder_id': d.folder_id.id,
            },
        }

    def action_create_shortcut_menu(self):
        d = self._doc()
        url = f"/web/content/custom.document/{d.id}/file/{d.file_name or 'file'}"
        rec = self.env['custom.document'].create({
            'name': f"Shortcut to {d.name}",
            'document_type': 'url',
            'url': url,
            'folder_id': d.folder_id.id,
            'tag_ids': [(6, 0, d.tag_ids.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }

    def action_manage_versions_menu(self):
        d = self._doc()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Versions'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('res_model', '=', 'custom.document'), ('res_id', '=', d.id)],
            'context': {'default_res_model': 'custom.document', 'default_res_id': d.id},
        }

    def action_lock_toggle_menu(self):
        d = self._doc()
        d.action_lock()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_copy_links_menu(self):
        d = self._doc()
        base = f"/web/content/custom.document/{d.id}/file/{d.file_name or 'file'}"
        raise UserError(_("Links:\nViewer: %s\nDownload: %s") % (base, base + "?download=true"))

    def action_split_pdf_menu(self):
        raise UserError(_("Split PDF: not implemented yet."))

    def action_sign_menu(self):
        raise UserError(_("Sign: integrate with Sign app if installed."))
