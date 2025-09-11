from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    document_ids = fields.One2many('documents.document', 'owner_id', string='Documents')


