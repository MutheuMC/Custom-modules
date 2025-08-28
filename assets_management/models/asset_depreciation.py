from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssetDepreciationLine(models.Model):
    _name = 'asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'date'
    
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        ondelete='cascade'
    )
    
    date = fields.Date(
        string='Depreciation Date',
        required=True,
        index=True
    )
    
    depreciation_amount = fields.Monetary(
        string='Depreciation Amount',
        required=True,
        currency_field='currency_id'
    )
    
    accumulated_depreciation = fields.Monetary(
        string='Accumulated Depreciation',
        compute='_compute_accumulated',
        store=True,
        currency_field='currency_id'
    )
    
    remaining_value = fields.Monetary(
        string='Remaining Value',
        compute='_compute_remaining',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        string='Currency'
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    
    company_id = fields.Many2one(
        related='asset_id.company_id',
        string='Company',
        store=True
    )
    
    @api.depends('asset_id', 'depreciation_amount')
    def _compute_accumulated(self):
        for line in self:
            previous_lines = line.asset_id.depreciation_line_ids.filtered(
                lambda l: l.date <= line.date and l.state == 'posted'
            )
            line.accumulated_depreciation = sum(previous_lines.mapped('depreciation_amount'))
    
    @api.depends('asset_id', 'accumulated_depreciation')
    def _compute_remaining(self):
        for line in self:
            line.remaining_value = line.asset_id.purchase_value - line.accumulated_depreciation
    
    def create_depreciation_entry(self):
        """Create journal entry for depreciation"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_('Only draft entries can be posted.'))
        
        if not self.asset_id.account_asset_id or not self.asset_id.account_depreciation_id or not self.asset_id.account_expense_id:
            raise UserError(_('Please configure accounts for the asset.'))
        
        # Create journal entry
        move_vals = {
            'date': self.date,
            'ref': f'Depreciation for {self.asset_id.name}',
            'journal_id': self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id)
            ], limit=1).id,
            'line_ids': [
                (0, 0, {
                    'name': f'Depreciation: {self.asset_id.name}',
                    'account_id': self.asset_id.account_expense_id.id,
                    'debit': self.depreciation_amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': f'Accumulated Depreciation: {self.asset_id.name}',
                    'account_id': self.asset_id.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': self.depreciation_amount,
                }),
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        self.write({
            'move_id': move.id,
            'state': 'posted'
        })
    
    def action_cancel(self):
        """Cancel depreciation entry"""
        for line in self:
            if line.state != 'posted':
                continue
            
            if line.move_id:
                if line.move_id.state == 'posted':
                    line.move_id.button_cancel()
                line.move_id.unlink()
            
            line.state = 'cancelled'