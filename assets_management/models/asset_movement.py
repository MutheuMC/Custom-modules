from odoo import models, fields, api, _


class AssetMovement(models.Model):
    _name = 'asset.movement'
    _description = 'Asset Movement'
    _order = 'date desc'
    _inherit = ['mail.thread']
    
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        tracking=True
    )
    
    date = fields.Datetime(
        string='Movement Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    movement_type = fields.Selection([
        ('transfer', 'Transfer'),
        ('assign', 'Assign'),
        ('return', 'Return'),
        ('repair', 'Send for Repair'),
        ('maintenance', 'Send for Maintenance'),
        ('location', 'Location Change')
    ], string='Movement Type', required=True, tracking=True)
    
    # From Information
    from_location_id = fields.Many2one(
        'stock.location',
        string='From Location',
        tracking=True
    )
    
    from_employee_id = fields.Many2one(
        'hr.employee',
        string='From Employee',
        tracking=True
    )
    
    from_department_id = fields.Many2one(
        'hr.department',
        string='From Department',
        tracking=True
    )
    
    # To Information
    to_location_id = fields.Many2one(
        'stock.location',
        string='To Location',
        tracking=True
    )
    
    to_employee_id = fields.Many2one(
        'hr.employee',
        string='To Employee',
        tracking=True
    )
    
    to_department_id = fields.Many2one(
        'hr.department',
        string='To Department',
        tracking=True
    )
    
    # Additional Information
    reason = fields.Text(string='Reason for Movement')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    company_id = fields.Many2one(
        related='asset_id.company_id',
        string='Company',
        store=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.movement') or _('New')
        return super(AssetMovement, self).create(vals)
    
    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'
    
    def action_done(self):
        self.ensure_one()
        # Update asset location and custodian
        if self.to_location_id:
            self.asset_id.location_id = self.to_location_id
        if self.to_employee_id:
            self.asset_id.custodian_id = self.to_employee_id
        if self.to_department_id:
            self.asset_id.department_id = self.to_department_id
        
        self.state = 'done'
    
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'