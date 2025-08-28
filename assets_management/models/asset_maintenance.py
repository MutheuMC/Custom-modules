from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class AssetMaintenance(models.Model):
    _name = 'asset.maintenance'
    _description = 'Asset Maintenance'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
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
    
    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('predictive', 'Predictive')
    ], string='Type', required=True, default='preventive')
    
    date = fields.Date(
        string='Maintenance Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    due_date = fields.Date(
        string='Due Date',
        tracking=True
    )
    
    completed_date = fields.Date(
        string='Completed Date',
        tracking=True
    )
    
    description = fields.Text(
        string='Description',
        required=True
    )
    
    performed_by = fields.Many2one(
        'hr.employee',
        string='Performed By'
    )
    
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain=[('supplier_rank', '>', 0)]
    )
    
    cost = fields.Monetary(
        string='Cost',
        currency_field='currency_id',
        tracking=True
    )
    
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        string='Currency'
    )
    
    duration = fields.Float(
        string='Duration (Hours)',
        help='Time taken for maintenance'
    )
    
    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='planned', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    # Recurring maintenance fields
    is_recurring = fields.Boolean(string='Is Recurring')
    
    recurrence_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string='Recurrence Type')
    
    recurrence_interval = fields.Integer(
        string='Recurrence Interval',
        default=1,
        help='Repeat every x days/weeks/months/years'
    )
    
    next_maintenance_date = fields.Date(
        string='Next Maintenance Date',
        compute='_compute_next_maintenance',
        store=True
    )
    
    company_id = fields.Many2one(
        related='asset_id.company_id',
        string='Company',
        store=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.maintenance') or _('New')
        return super(AssetMaintenance, self).create(vals)
    
    @api.depends('is_recurring', 'recurrence_type', 'recurrence_interval', 'completed_date')
    def _compute_next_maintenance(self):
        for maintenance in self:
            if maintenance.is_recurring and maintenance.completed_date:
                if maintenance.recurrence_type == 'daily':
                    maintenance.next_maintenance_date = maintenance.completed_date + timedelta(days=maintenance.recurrence_interval)
                elif maintenance.recurrence_type == 'weekly':
                    maintenance.next_maintenance_date = maintenance.completed_date + timedelta(weeks=maintenance.recurrence_interval)
                elif maintenance.recurrence_type == 'monthly':
                    maintenance.next_maintenance_date = maintenance.completed_date + relativedelta(months=maintenance.recurrence_interval)
                elif maintenance.recurrence_type == 'yearly':
                    maintenance.next_maintenance_date = maintenance.completed_date + relativedelta(years=maintenance.recurrence_interval)
            else:
                maintenance.next_maintenance_date = False
    
    def action_start(self):
        self.ensure_one()
        self.state = 'in_progress'
        self.asset_id.state = 'in_maintenance'
    
    def action_done(self):
        self.ensure_one()
        self.write({
            'state': 'done',
            'completed_date': fields.Date.today()
        })
        self.asset_id.state = 'in_use'
        
        # Create next maintenance if recurring
        if self.is_recurring and self.next_maintenance_date:
            self.copy({
                'date': self.next_maintenance_date,
                'state': 'planned',
                'completed_date': False
            })
    
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'
        if self.asset_id.state == 'in_maintenance':
            self.asset_id.state = 'in_use'
    
    @api.model
    def cron_create_recurring_maintenance(self):
        """Cron job to create recurring maintenance records"""
        today = fields.Date.today()
        
        # Find completed recurring maintenances that need new records
        maintenances = self.search([
            ('is_recurring', '=', True),
            ('state', '=', 'done'),
            ('next_maintenance_date', '<=', today)
        ])
        
        for maintenance in maintenances:
            # Check if maintenance already exists for this date
            existing = self.search([
                ('asset_id', '=', maintenance.asset_id.id),
                ('date', '=', maintenance.next_maintenance_date),
                ('state', '!=', 'cancelled')
            ], limit=1)
            
            if not existing:
                maintenance.copy({
                    'date': maintenance.next_maintenance_date,
                    'state': 'planned',
                    'completed_date': False
                })