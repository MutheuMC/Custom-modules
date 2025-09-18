from odoo import models, fields, _, api
from odoo.exceptions import UserError


class CustomDocumentPreviewActionsWizard(models.TransientModel):
    _name = 'custom.document.preview.actions.wizard'
    _description = 'Preview Actions Wizard'

    document_id = fields.Many2one('custom.document', required=True, readonly=True)

    # ---- Actions ----

    def _ensure_doc(self):
        self.ensure_one()
        if not self.document_id:
            raise UserError(_("No document found."))

    def action_duplicate(self):
        self._ensure_doc()
        vals = {
            'name': (self.document_id.name or '') + ' (copy)',
            'document_type': self.document_id.document_type,
            'file': self.document_id.with_context(bin_size=False).file,
            'file_name': self.document_id.file_name,
            'mimetype': self.document_id.mimetype,
            'url': self.document_id.url,
            'folder_id': self.document_id.folder_id.id,
            'tag_ids': [(6, 0, self.document_id.tag_ids.ids)],
        }
        copy = self.document_id.sudo().create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'form',
            'res_id': copy.id,
            'target': 'current',
        }

    def action_move_to_trash(self):
        self._ensure_doc()
        self.document_id.sudo().write({'active': False})
        return {'type': 'ir.actions.act_window_close'}

    def action_lock_toggle(self):
        self._ensure_doc()
        self.document_id.sudo().action_lock()
        return {'type': 'ir.actions.act_window_close'}

    def action_copy_links(self):
        self._ensure_doc()
        # viewer-like link (download=False) + download link
        base_view = f"/web/content/custom.document/{self.document_id.id}/file/{self.document_id.file_name or 'file'}"
        viewer = base_view
        download = base_view + "?download=true"
        raise UserError(_("Links:\nViewer: %s\nDownload: %s") % (viewer, download))

    def action_manage_versions(self):
        self._ensure_doc()
        # Open the attachment(s) used to store the binary
        return {
            'type': 'ir.actions.act_window',
            'name': _('Versions'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [
                ('res_model', '=', 'custom.document'),
                ('res_id', '=', self.document_id.id),
            ],
            'context': {'default_res_model': 'custom.document', 'default_res_id': self.document_id.id},
        }

    def action_create_shortcut(self):
        self._ensure_doc()
        url = f"/web/content/custom.document/{self.document_id.id}/file/{self.document_id.file_name or 'file'}"
        rec = self.env['custom.document'].sudo().create({
            'name': f"Shortcut to {self.document_id.name}",
            'document_type': 'url',
            'url': url,
            'folder_id': self.document_id.folder_id.id,
            'tag_ids': [(6, 0, self.document_id.tag_ids.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }

    def action_rename(self):
        self._ensure_doc()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rename'),
            'res_model': 'custom.document.rename.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.document_id.id,
                'default_new_name': self.document_id.name,
            },
        }

    def action_info_and_tags(self):
        self._ensure_doc()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Info & tags'),
            'res_model': 'custom.document.properties.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.document_id.id,
                'default_name': self.document_id.name,
                'default_tag_ids': [(6, 0, self.document_id.tag_ids.ids)],
                'default_folder_id': self.document_id.folder_id.id,
            },
        }

    def action_split_pdf(self):
        raise UserError(_("Split PDF: not implemented yet."))

    def action_sign(self):
        raise UserError(_("Sign: please integrate with the Sign app if installed."))
