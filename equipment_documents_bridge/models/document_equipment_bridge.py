# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CustomDocumentEquipmentBridge(models.Model):
    _inherit = 'custom.document'

    # ------------- Equipment Link -------------

    equipment_id = fields.Many2one(
        'equipment.item',
        string='Related Equipment',
        help='Equipment item this document belongs to',
        index=True,
        ondelete='cascade',
    )

    # ------------- Folder → Equipment Resolver -------------

    def _find_equipment_from_folder(self, folder_id):
        """
        Find equipment by traversing folder hierarchy upward.
        Returns equipment ID or False.

        Assumes:
        - equipment.item model exists (because this module depends on the
          equipment module),
        - equipment.item has a Many2one to custom.document.folder named
          'equipment_folder_id'.
        """
        if not folder_id:
            return False

        FolderModel = self.env['custom.document.folder'].sudo()
        folder = FolderModel.browse(folder_id)

        max_depth = 10
        depth = 0

        while folder and folder.exists() and depth < max_depth:
            # Check if this folder belongs to an equipment
            equipment = self.env['equipment.item'].sudo().search([
                ('equipment_folder_id', '=', folder.id)
            ], limit=1)

            if equipment and equipment.exists():
                return equipment.id

            # Move up to parent folder
            folder = folder.parent_id
            depth += 1

        return False

    # ------------- Create / Write Hooks -------------

    @api.model_create_multi
    def create(self, vals_list):
        """
        After creating the document(s), automatically link to equipment
        if a folder implies an equipment, and equipment_id is not already set.
        """
        records = super().create(vals_list)

        # Use context flag to avoid infinite loops if we need to write again
        if self.env.context.get('skip_equipment_autolink'):
            return records

        for doc in records:
            if not doc.equipment_id and doc.folder_id:
                equipment_id = doc._find_equipment_from_folder(doc.folder_id.id)
                if equipment_id:
                    # Avoid re-triggering our own logic
                    doc.with_context(skip_equipment_autolink=True).write({
                        'equipment_id': equipment_id
                    })

        return records

    def write(self, vals):
        """
        When folder changes (and equipment_id not explicitly given),
        re-evaluate which equipment (if any) this document should belong to.
        """
        # If we are already in an internal write from our own logic, skip
        if self.env.context.get('skip_equipment_autolink'):
            return super().write(vals)

        res = super().write(vals)

        # Only do work if folder changed and caller did NOT explicitly set equipment_id
        if 'folder_id' in vals and 'equipment_id' not in vals:
            for doc in self:
                if doc.folder_id:
                    equipment_id = doc._find_equipment_from_folder(doc.folder_id.id)
                    if equipment_id and doc.equipment_id.id != equipment_id:
                        doc.with_context(skip_equipment_autolink=True).write({
                            'equipment_id': equipment_id
                        })

        return res
