# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CustomDocumentEquipmentBridge(models.Model):
    _inherit = 'custom.document'

    # Link from Document → Equipment
    equipment_id = fields.Many2one(
        'equipment.item',
        string='Related Equipment',
        help='Equipment item this document belongs to',
        index=True,
        ondelete='cascade',
    )

    def _find_equipment_from_folder(self, folder_id):
        """Walk folders upwards to find the owning equipment, if any."""
        if not folder_id:
            return False

        Folder = self.env['custom.document.folder'].sudo()
        folder = Folder.browse(folder_id)

        max_depth = 10
        depth = 0

        while folder and folder.exists() and depth < max_depth:
            equipment = self.env['equipment.item'].sudo().search([
                ('equipment_folder_id', '=', folder.id)
            ], limit=1)
            if equipment:
                return equipment.id
            folder = folder.parent_id
            depth += 1

        return False

    @api.model_create_multi
    def create(self, vals_list):
        docs = super().create(vals_list)

        if self.env.context.get('skip_equipment_autolink'):
            return docs

        # Auto-link to equipment after creation based on folder
        for doc in docs:
            if not doc.equipment_id and doc.folder_id:
                eid = doc._find_equipment_from_folder(doc.folder_id.id)
                if eid:
                    doc.with_context(skip_equipment_autolink=True).write({'equipment_id': eid})
        return docs

    def write(self, vals):
        if self.env.context.get('skip_equipment_autolink'):
            return super().write(vals)

        res = super().write(vals)

        # If folder changed and equipment_id wasn't explicitly given, recompute link
        if 'folder_id' in vals and 'equipment_id' not in vals:
            for doc in self:
                if doc.folder_id:
                    eid = doc._find_equipment_from_folder(doc.folder_id.id)
                    if eid and doc.equipment_id.id != eid:
                        doc.with_context(skip_equipment_autolink=True).write({'equipment_id': eid})
        return res


class EquipmentItemDocumentBridge(models.Model):
    _inherit = 'equipment.item'

    # One2many defined HERE (in the bridge), not in equipment_management
    document_ids = fields.One2many(
        'custom.document',
        'equipment_id',
        string='Documents'
    )
