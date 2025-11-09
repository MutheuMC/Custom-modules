from odoo import models, fields

class CustomDocumentTag(models.Model):
    _name = 'custom.document.tag'
    _description = 'Document Tag'
    
    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color Index')
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name already exists!'),
    ]