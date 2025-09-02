from odoo import models, fields, api

class OfficeLocation(models.Model):
    _name = 'office.location'
    _description = 'Office Location'
    _order = 'name'
    
    name = fields.Char(string='Office Name', required=True)
    code = fields.Char(string='Office Code')
    department = fields.Char(string='Department')
    
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person')
    backup_person_id = fields.Many2one('res.users', string='Backup Person')
    
    email = fields.Char(string='Office Email')
    phone = fields.Char(string='Office Phone')
    
    address = fields.Text(string='Address')
    
    # Statistics
    document_count = fields.Integer(string='Documents Here', compute='_compute_document_count')
    incoming_count = fields.Integer(string='Incoming Today', compute='_compute_incoming_count')
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('name')
    def _compute_document_count(self):
        for record in self:
            record.document_count = self.env['document.tracker'].search_count([
                ('current_location_id', '=', record.id),
                ('status', 'not in', ['returned', 'completed', 'lost'])
            ])
    
    @api.depends('name')
    def _compute_incoming_count(self):
        today = fields.Date.today()
        for record in self:
            record.incoming_count = self.env['document.movement'].search_count([
                ('to_location_id', '=', record.id),
                ('taken_date', '>=', today),
                ('status', '=', 'taken')
            ])