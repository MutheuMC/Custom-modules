# -*- coding: utf-8 -*-
from odoo import api, fields, models

class DocumentsTag(models.Model):
    _name = 'documents.tag'
    _description = 'Document Tag'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True, string='Active')

    folder_id = fields.Many2one('documents.folder', string='Folder',
                                help='Folder where this tag is available')
    facet_id = fields.Many2one('documents.facet', string='Category',
                               ondelete='cascade')

    _sql_constraints = [
        ('unique_tag', 'UNIQUE(name, folder_id, facet_id)',
         'Tag must be unique per folder and category!')
    ]

class DocumentsFacet(models.Model):
    _name = 'documents.facet'
    _description = 'Document Tag Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    folder_id = fields.Many2one('documents.folder', string='Folder')
    tag_ids = fields.One2many('documents.tag', 'facet_id', string='Tags')
    tooltip = fields.Char(string='Tooltip')
