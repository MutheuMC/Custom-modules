from odoo import models, fields, api
from datetime import datetime, timedelta

class DocumentTracker(models.Model):
    _name = 'document.tracker'
    _description = 'Document Tracker'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(string='Document Number', required=True, tracking=True,
                      default=lambda self: 'New')
    
    document_type = fields.Selection([
        ('claim', 'Claim'),
        ('contract', 'Contract Letter'),
        ('hr_letter', 'HR Letter'),
        ('finance_letter', 'Finance Letter'),
        ('vc_letter', 'VC Letter'),
        ('other', 'Other')
    ], string='Document Type', required=True, tracking=True)
    
    title = fields.Char(string='Title/Subject', required=True, tracking=True)
    description = fields.Text(string='Description')
    
    # File upload fields
    document_file = fields.Binary(string='Document File')
    document_filename = fields.Char(string='File Name')
    document_scan = fields.Binary(string='Scanned Document')
    scan_filename = fields.Char(string='Scan File Name')
    
    # Current status fields
    current_location_id = fields.Many2one('office.location', string='Current Location', tracking=True)
    current_holder_id = fields.Many2one('res.users', string='Current Holder', tracking=True)
    
    status = fields.Selection([
        ('created', 'Created'),
        ('available', 'Available'),
        ('in_transit', 'In Transit'),
        ('at_office', 'At Office'),
        ('returned', 'Returned'),
        ('completed', 'Completed'),
        ('lost', 'Lost')
    ], string='Status', default='created', tracking=True)
    
    # Movement tracking
    movement_ids = fields.One2many('document.movement', 'document_id', string='Movement History')
    movement_count = fields.Integer(string='Total Movements', compute='_compute_movement_count')
    
    # Dates
    date_created = fields.Datetime(string='Date Created', default=fields.Datetime.now)
    last_movement_date = fields.Datetime(string='Last Movement', compute='_compute_last_movement')
    expected_return_date = fields.Date(string='Expected Return Date')
    
    # Additional fields
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='0')
    
    is_overdue = fields.Boolean(string='Is Overdue', compute='_compute_overdue')
    days_in_current_location = fields.Integer(string='Days in Current Location', compute='_compute_days_in_location')
    
    # Barcode/QR Code
    barcode = fields.Char(string='Barcode/QR Code', copy=False)
    
    @api.depends('movement_ids')
    def _compute_movement_count(self):
        for record in self:
            record.movement_count = len(record.movement_ids)
    
    @api.depends('movement_ids')
    def _compute_last_movement(self):
        for record in self:
            if record.movement_ids:
                record.last_movement_date = max(record.movement_ids.mapped('taken_date'))
            else:
                record.last_movement_date = record.date_created
    
    @api.depends('expected_return_date')
    def _compute_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = bool(record.expected_return_date and record.expected_return_date < today 
                                    and record.status not in ['returned', 'completed'])
    
    @api.depends('last_movement_date')
    def _compute_days_in_location(self):
        now = datetime.now()
        for record in self:
            if record.last_movement_date:
                delta = now - record.last_movement_date
                record.days_in_current_location = delta.days
            else:
                record.days_in_current_location = 0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('document.tracker') or 'New'
            if not vals.get('barcode'):
                vals['barcode'] = vals.get('name')
        return super(DocumentTracker, self).create(vals_list)
    
    def action_move_document(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Move Document',
            'res_model': 'document.movement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_from_location_id': self.current_location_id.id,
            }
        }
    
    def action_view_movements(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Document Movements',
            'res_model': 'document.movement',
            'view_mode': 'tree,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id}
        }
    
    def action_return_document(self):
        self.status = 'returned'
        return True
    
    def action_mark_lost(self):
        self.status = 'lost'
        return True