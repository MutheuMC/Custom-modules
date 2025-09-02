from odoo import models, fields, api
from datetime import datetime

class DocumentMovement(models.Model):
    _name = 'document.movement'
    _description = 'Document Movement'
    _order = 'taken_date desc'
    _inherit = ['mail.thread']
    
    document_id = fields.Many2one('document.tracker', string='Document', 
                                 required=True, ondelete='cascade')
    document_type = fields.Selection(related='document_id.document_type', 
                                    string='Document Type', store=True)
    
    from_location_id = fields.Many2one('office.location', string='From Location')
    to_location_id = fields.Many2one('office.location', string='To Location', required=True)
    
    taken_by_id = fields.Many2one('res.users', string='Taken By', 
                                  required=True, default=lambda self: self.env.user)
    received_by_id = fields.Many2one('res.users', string='Received By')
    
    taken_date = fields.Datetime(string='Taken Date', default=fields.Datetime.now, required=True)
    received_date = fields.Datetime(string='Received Date')
    return_date = fields.Datetime(string='Return Date')
    
    expected_return_date = fields.Date(string='Expected Return')
    
    purpose = fields.Text(string='Purpose/Reason')
    notes = fields.Text(string='Notes')
    
    status = fields.Selection([
        ('taken', 'Taken'),
        ('received', 'Received'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='taken', tracking=True)
    
    # Duration calculation
    duration_hours = fields.Float(string='Duration (Hours)', compute='_compute_duration')
    
    @api.depends('taken_date', 'return_date')
    def _compute_duration(self):
        for record in self:
            if record.taken_date and record.return_date:
                delta = record.return_date - record.taken_date
                record.duration_hours = delta.total_seconds() / 3600
            else:
                record.duration_hours = 0
    
    @api.model
    def create(self, vals):
        movement = super(DocumentMovement, self).create(vals)
        # Update document status and location
        if movement.document_id:
            movement.document_id.write({
                'status': 'in_transit',
                'current_location_id': movement.to_location_id.id,
                'current_holder_id': movement.taken_by_id.id,
            })
        return movement
    
    def action_confirm_receipt(self):
        self.write({
            'status': 'received',
            'received_date': fields.Datetime.now(),
            'received_by_id': self.env.user.id,
        })
        self.document_id.status = 'at_office'
        return True
    
    def action_return(self):
        self.write({
            'status': 'returned',
            'return_date': fields.Datetime.now(),
        })
        self.document_id.status = 'returned'
        return True
