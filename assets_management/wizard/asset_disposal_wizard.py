from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssetDisposalWizard(models.TransientModel):
    _name = 'asset.disposal.wizard'
    _description = 'Asset Disposal Wizard'
    
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True
    )
    
    disposal_type = fields.Selection([
        ('sale', 'Sale'),
        ('scrap', 'Scrap'),
        ('donate', 'Donation'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged Beyond Repair')
    ], string='Disposal Type', required=True, default='sale')
    
    disposal_date = fields.Date(
        string='Disposal Date',
        required=True,
        default=fields.Date.context_today
    )
    
    disposal_value = fields.Monetary(
        string='Disposal Value',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        string='Currency'
    )
    
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        domain=[('customer_rank', '>', 0)]
    )
    
    reason = fields.Text(string='Disposal Reason')
    
    create_journal_entry = fields.Boolean(
        string='Create Journal Entry',
        default=True
    )
    
    def action_dispose(self):
        self.ensure_one()
        
        if self.disposal_type == 'sale' and not self.disposal_value:
            raise UserError(_('Please enter the sale value.'))
        
        # Create final depreciation entry if needed
        if self.create_journal_entry:
            self._create_disposal_journal_entry()
        
        # Update asset status
        disposal_state_map = {
            'sale': 'sold',
            'scrap': 'disposed',
            'donate': 'disposed',
            'lost': 'lost',
            'damaged': 'damaged'
        }
        
        self.asset_id.write({
            'state': disposal_state_map.get(self.disposal_type, 'disposed'),
            'active': False
        })
        
        # Create disposal log
        message = f"Asset disposed: Type={self.disposal_type}, Date={self.disposal_date}"
        if self.disposal_value:
            message += f", Value={self.disposal_value}"
        if self.reason:
            message += f", Reason={self.reason}"
        
        self.asset_id.message_post(body=message)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _create_disposal_journal_entry(self):
        """Create journal entry for asset disposal"""
        asset = self.asset_id
        
        if not asset.account_asset_id or not asset.account_depreciation_id:
            raise UserError(_('Please configure accounts for the asset.'))
        
        # Calculate gain/loss on disposal
        book_value = asset.current_value
        disposal_value = self.disposal_value or 0
        gain_loss = disposal_value - book_value
        
        # Determine gain/loss account
        if gain_loss >= 0:
            gain_loss_account = self.env['account.account'].search([
                ('account_type', '=', 'income_other'),
                ('company_id', '=', asset.company_id.id)
            ], limit=1)
        else:
            gain_loss_account = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
                ('company_id', '=', asset.company_id.id)
            ], limit=1)
        
        if not gain_loss_account:
            raise UserError(_('Please configure gain/loss account.'))
        
        # Create journal entry
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', asset.company_id.id)
        ], limit=1)
        
        if not journal:
            raise UserError(_('Please configure a general journal.'))
        
        move_lines = []
        
        # Debit accumulated depreciation
        if asset.accumulated_depreciation:
            move_lines.append((0, 0, {
                'name': f'Disposal: {asset.name} - Accumulated Depreciation',
                'account_id': asset.account_depreciation_id.id,
                'debit': asset.accumulated_depreciation,
                'credit': 0.0,
            }))
        
        # Credit asset account
        move_lines.append((0, 0, {
            'name': f'Disposal: {asset.name} - Asset Value',
            'account_id': asset.account_asset_id.id,
            'debit': 0.0,
            'credit': asset.purchase_value,
        }))
        
        # Record disposal value (if any)
        if disposal_value > 0:
            # Debit cash/receivable
            cash_account = self.env['account.account'].search([
                ('account_type', '=', 'asset_cash'),
                ('company_id', '=', asset.company_id.id)
            ], limit=1)
            
            move_lines.append((0, 0, {
                'name': f'Disposal: {asset.name} - Sale Proceeds',
                'account_id': cash_account.id if cash_account else gain_loss_account.id,
                'debit': disposal_value,
                'credit': 0.0,
            }))
        
        # Record gain/loss
        if gain_loss != 0:
            if gain_loss > 0:
                move_lines.append((0, 0, {
                    'name': f'Disposal: {asset.name} - Gain on Disposal',
                    'account_id': gain_loss_account.id,
                    'debit': 0.0,
                    'credit': abs(gain_loss),
                }))
            else:
                move_lines.append((0, 0, {
                    'name': f'Disposal: {asset.name} - Loss on Disposal',
                    'account_id': gain_loss_account.id,
                    'debit': abs(gain_loss),
                    'credit': 0.0,
                }))
        
        move_vals = {
            'date': self.disposal_date,
            'ref': f'Asset Disposal: {asset.name}',
            'journal_id': journal.id,
            'line_ids': move_lines
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
