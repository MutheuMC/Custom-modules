from odoo import models, fields, api

class DocumentMovementWizard(models.TransientModel):
    _name = 'document.movement.wizard'
    _description = 'Document Movement Wizard'
    
    document_id = fields.Many2one('document.tracker', string='Document', required=True)
    from_location_id = fields.Many2one('office.location', string='From Location')
    to_location_id = fields.Many2one('office.location', string='To Location', required=True)
    
    taken_by_id = fields.Many2one('res.users', string='Person Taking Document', 
                                  required=True, default=lambda self: self.env.user)
    
    purpose = fields.Text(string='Purpose/Reason for Movement', required=True)
    expected_return_date = fields.Date(string='Expected Return Date')
    notes = fields.Text(string='Additional Notes')
    
    send_notification = fields.Boolean(string='Send Email Notification', default=True)
    
    def action_move_document(self):
        movement_vals = {
            'document_id': self.document_id.id,
            'from_location_id': self.from_location_id.id,
            'to_location_id': self.to_location_id.id,
            'taken_by_id': self.taken_by_id.id,
            'purpose': self.purpose,
            'expected_return_date': self.expected_return_date,
            'notes': self.notes,
            'status': 'taken',
        }
        
        movement = self.env['document.movement'].create(movement_vals)
        
        # Update document
        self.document_id.write({
            'current_location_id': self.to_location_id.id,
            'current_holder_id': self.taken_by_id.id,
            'status': 'in_transit',
            'expected_return_date': self.expected_return_date,
        })
        
        # Send notification if requested
        if self.send_notification and self.to_location_id.responsible_person_id:
            self._send_movement_notification(movement)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _send_movement_notification(self, movement):
        # Email notification logic here
        pass