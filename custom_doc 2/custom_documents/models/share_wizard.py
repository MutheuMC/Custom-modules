# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CustomDocumentShareWizard(models.TransientModel):
    _name = 'custom.document.share.wizard'
    _description = 'Share Document'

    document_id  = fields.Many2one('custom.document', required=True, readonly=True)

    # add this field
    document_name = fields.Char(related='document_id.display_name', string='Document', readonly=True)


    # Add people
    partner_ids  = fields.Many2many('res.partner', string="Add people")
    role         = fields.Selection([('viewer','Viewer'),('commenter','Commenter'),('editor','Editor')], default='viewer')

    # Existing people (editable inline)
    people_ids   = fields.One2many(related='document_id.share_line_ids', readonly=False)

    # General access (drive-style)
    share_access = fields.Selection(related='document_id.share_access', readonly=False)

    # Links for quick copy
    view_link = fields.Char(compute='_compute_links')
    edit_link = fields.Char(compute='_compute_links')

    def _compute_links(self):
        for w in self:
            w.view_link = w.document_id.get_share_link('view')
            w.edit_link = w.document_id.get_share_link('edit')

    def action_add_people(self):
        self.ensure_one()
        for p in self.partner_ids:
            self.env['custom.document.share.line'].create({
                'document_id': self.document_id.id,
                'partner_id':  p.id,
                'role':        self.role,
            })
        self.partner_ids = [(5, 0, 0)]  # clear selection
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_copy_view_link(self):
        self.ensure_one()
        raise UserError(_("View link:\n%s") % (self.view_link,))

    def action_copy_edit_link(self):
        self.ensure_one()
        raise UserError(_("Edit link:\n%s") % (self.edit_link,))
