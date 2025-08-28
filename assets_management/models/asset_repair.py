from odoo import models, fields, api, _


class AssetRepair(models.Model):
    _name = 'asset.repair'
    _description = 'Asset Repair'
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
    
    date = fields.Date(
        string='Repair Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    completed_date = fields.Date(
        string='Completed Date',
        tracking=True
    )
    
    problem_description = fields.Text(
        string='Problem Description',
        required=True
    )
    
    repair_description = fields.Text(
        string='Repair Description'
    )
    
    vendor_id = fields.Many2one(
        'res.partner',
        string='Repair Vendor',
        domain=[('supplier_rank', '>', 0)]
    )
    
    technician = fields.Char(string='Technician Name')
    
    cost = fields.Monetary(
        string='Repair Cost',
        currency_field='currency_id',
        tracking=True
    )
    
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        string='Currency'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Vendor Invoice',
        domain=[('move_type', '=', 'in_invoice')]
    )
    
    state = fields.Selection([
        ('reported', 'Reported'),
        ('confirmed', 'Confirmed'),
        ('in_repair', 'In Repair'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='reported', tracking=True)
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority', default='medium')
    
    warranty_claim = fields.Boolean(string='Warranty Claim')
    
    notes = fields.Text(string='Additional Notes')
    
    company_id = fields.Many2one(
        related='asset_id.company_id',
        string='Company',
        store=True
    )


 

    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.repair') or _('New')
        return super(AssetRepair, self).create(vals)
    
    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'
    
    def action_start_repair(self):
        self.ensure_one()
        self.state = 'in_repair'
        self.asset_id.state = 'in_repair'
    
    def action_done(self):
        self.ensure_one()
        self.write({
            'state': 'done',
            'completed_date': fields.Date.today()
        })
        self.asset_id.state = 'in_use'
    
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'
        if self.asset_id.state == 'in_repair':
            self.asset_id.state = 'in_use'



    def action_view_asset(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asset.asset',
            'view_mode': 'form',
            'res_id': self.asset_id.id,
            'target': 'current',
        }