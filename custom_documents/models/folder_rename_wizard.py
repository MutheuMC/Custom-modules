# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class CustomFolderRenameWizard(models.TransientModel):
    _name = 'custom.document.folder.rename.wizard'
    _description = 'Rename Folder Wizard'
    
    folder_id = fields.Many2one('custom.document.folder', required=True, readonly=True)
    new_name = fields.Char('New name', required=True)

    def action_apply(self):
        self.ensure_one()
        if not self.new_name:
            raise UserError(_("Please provide a name."))
        self.folder_id.sudo().write({'name': self.new_name})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }