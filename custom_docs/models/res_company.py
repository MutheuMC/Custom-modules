# custom_documents/models/res_company.py
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    documents_folder_id = fields.Many2one('documents.folder', string='Documents Folder',
                                          help='Main folder for company documents')
    documents_tags_ids = fields.Many2many('documents.tag', string='Document Tags')