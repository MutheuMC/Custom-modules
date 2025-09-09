from odoo import models, fields, api

class DocumentTag(models.Model):
    _name = 'document.tag'
    _description = 'Document Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)
    document_ids = fields.Many2many(
        'document.document', 'document_tag_rel',
        'tag_id', 'document_id', string='Documents')