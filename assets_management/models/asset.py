from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class Asset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(
        string='Asset Name',
        required=True,
        tracking=True,
        index=True
    )

    asset_code = fields.Char(
        string='Asset Code',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )

    asset_tag = fields.Char(
        string='Asset Tag',
        help='Physical tag or label on the asset'
    )

    barcode = fields.Char(
        string='Barcode',
        copy=False,
        help='Barcode for scanning'
    )

    category_id = fields.Many2one(
        'asset.category',
        string='Asset Category',
        required=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('in_use', 'In Use'),
        ('in_maintenance', 'In Maintenance'),
        ('in_repair', 'In Repair'),
        ('disposed', 'Disposed'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('sold', 'Sold')
    ], string='Status', default='draft', tracking=True, index=True)

    # Asset Details
    asset_type = fields.Selection([
        ('fixed', 'Fixed Asset'),
        ('movable', 'Movable Asset'),
        ('intangible', 'Intangible Asset'),
        ('lease', 'Leased Asset')
    ], string='Asset Type', required=True, default='fixed')

    description = fields.Text(string='Description')

    model = fields.Char(string='Model')
    serial_no = fields.Char(string='Serial Number')
    manufacturer = fields.Char(string='Manufacturer')

    # Purchase Information
    purchase_date = fields.Date(
        string='Purchase Date',
        required=True,
        tracking=True,
        default=fields.Date.context_today
    )

    purchase_value = fields.Monetary(
        string='Purchase Value',
        required=True,
        tracking=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain=[('supplier_rank', '>', 0)]
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Purchase Invoice',
        domain=[('move_type', '=', 'in_invoice')]
    )

    # Depreciation Information
    depreciation_method = fields.Selection([
        ('straight', 'Straight Line'),
        ('declining', 'Declining Balance'),
        ('double_declining', 'Double Declining Balance'),
        ('manual', 'Manual')
    ], string='Depreciation Method', default='straight', required=True)

    depreciation_rate = fields.Float(
        string='Depreciation Rate (%)',
        help='Annual depreciation rate as percentage'
    )

    useful_life = fields.Integer(
        string='Useful Life (Years)',
        help='Expected useful life in years'
    )

    salvage_value = fields.Monetary(
        string='Salvage Value',
        currency_field='currency_id',
        help='Expected value at end of useful life'
    )

    depreciation_start_date = fields.Date(
        string='Depreciation Start Date',
        help='Date when depreciation calculation starts'
    )

    current_value = fields.Monetary(
        string='Current Book Value',
        compute='_compute_current_value',
        store=True,
        currency_field='currency_id'
    )

    accumulated_depreciation = fields.Monetary(
        string='Accumulated Depreciation',
        compute='_compute_accumulated_depreciation',
        store=True,
        currency_field='currency_id'
    )

    # Location Information
    location_id = fields.Many2one(
        'stock.location',
        string='Current Location'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        tracking=True
    )

    custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodian',
        tracking=True,
        help='Employee responsible for the asset'
    )

    # Warranty Information
    warranty_start_date = fields.Date(string='Warranty Start Date')
    warranty_end_date = fields.Date(string='Warranty End Date')
    warranty_vendor_id = fields.Many2one(
        'res.partner',
        string='Warranty Vendor'
    )

    # Insurance Information
    is_insured = fields.Boolean(string='Is Insured')
    insurance_company = fields.Char(string='Insurance Company')
    insurance_policy_no = fields.Char(string='Policy Number')
    insurance_premium = fields.Monetary(
        string='Insurance Premium',
        currency_field='currency_id'
    )
    insurance_start_date = fields.Date(string='Insurance Start Date')
    insurance_end_date = fields.Date(string='Insurance End Date')

    # Accounting Information
    account_asset_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        domain=[('account_type', '=', 'asset_fixed')]
    )

    account_depreciation_id = fields.Many2one(
        'account.account',
        string='Depreciation Account',
        domain=[('account_type', '=', 'asset_fixed')]
    )

    account_expense_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        domain=[('account_type', '=', 'expense')]
    )

    # Related Records
    depreciation_line_ids = fields.One2many(
        'asset.depreciation.line',
        'asset_id',
        string='Depreciation Lines'
    )

    movement_ids = fields.One2many(
        'asset.movement',
        'asset_id',
        string='Movement History'
    )

    maintenance_ids = fields.One2many(
        'asset.maintenance',
        'asset_id',
        string='Maintenance Records'
    )

    repair_ids = fields.One2many(
        'asset.repair',
        'asset_id',
        string='Repair Records'
    )

    # Additional Information
    notes = fields.Text(string='Notes')

    image = fields.Binary(string='Image', attachment=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    active = fields.Boolean(default=True)

    # Computed fields for dashboard/stat buttons
    movement_count = fields.Integer(
        compute='_compute_movement_count',
        string='Movement Count'
    )
    maintenance_count = fields.Integer(
        compute='_compute_maintenance_count',
        string='Maintenance Count'
    )
    repair_count = fields.Integer(
        compute='_compute_repair_count',
        string='Repair Count'
    )

    total_maintenance_cost = fields.Monetary(
        compute='_compute_total_costs',
        string='Total Maintenance Cost',
        currency_field='currency_id'
    )

    total_repair_cost = fields.Monetary(
        compute='_compute_total_costs',
        string='Total Repair Cost',
        currency_field='currency_id'
    )

    @api.model
    def create(self, vals):
        if vals.get('asset_code', _('New')) == _('New'):
            vals['asset_code'] = self.env['ir.sequence'].next_by_code('asset.asset') or _('New')

        # Set depreciation start date if not provided
        if not vals.get('depreciation_start_date') and vals.get('purchase_date'):
            vals['depreciation_start_date'] = vals['purchase_date']

        # Get default accounts from category if not set
        if vals.get('category_id'):
            category = self.env['asset.category'].browse(vals['category_id'])
            if not vals.get('account_asset_id'):
                vals['account_asset_id'] = category.account_asset_id.id
            if not vals.get('account_depreciation_id'):
                vals['account_depreciation_id'] = category.account_depreciation_id.id
            if not vals.get('account_expense_id'):
                vals['account_expense_id'] = category.account_expense_id.id
            if not vals.get('depreciation_method'):
                vals['depreciation_method'] = category.depreciation_method
            if not vals.get('depreciation_rate'):
                vals['depreciation_rate'] = category.depreciation_rate
            if not vals.get('useful_life'):
                vals['useful_life'] = category.useful_life

        return super(Asset, self).create(vals)

    @api.depends('purchase_value', 'accumulated_depreciation')
    def _compute_current_value(self):
        for asset in self:
            asset.current_value = asset.purchase_value - asset.accumulated_depreciation

    @api.depends('depreciation_line_ids.depreciation_amount')
    def _compute_accumulated_depreciation(self):
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered(lambda l: l.state == 'posted')
            asset.accumulated_depreciation = sum(posted_lines.mapped('depreciation_amount'))

    @api.depends('movement_ids')
    def _compute_movement_count(self):
        for asset in self:
            asset.movement_count = len(asset.movement_ids)

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for asset in self:
            asset.maintenance_count = len(asset.maintenance_ids)

    @api.depends('repair_ids')
    def _compute_repair_count(self):
        for asset in self:
            asset.repair_count = len(asset.repair_ids)

    @api.depends('maintenance_ids.cost', 'repair_ids.cost')
    def _compute_total_costs(self):
        for asset in self:
            asset.total_maintenance_cost = sum(asset.maintenance_ids.mapped('cost'))
            asset.total_repair_cost = sum(asset.repair_ids.mapped('cost'))

    def action_submit(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft assets can be submitted.'))
        self.state = 'submit'

    def action_approve(self):
        self.ensure_one()
        if self.state != 'submit':
            raise UserError(_('Only submitted assets can be approved.'))

        # Generate depreciation schedule
        self.generate_depreciation_schedule()
        self.state = 'approve'

    def action_set_to_use(self):
        self.ensure_one()
        if self.state != 'approve':
            raise UserError(_('Only approved assets can be set to use.'))
        self.state = 'in_use'

    def action_dispose(self):
        self.ensure_one()
        # Open disposal wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dispose Asset'),
            'res_model': 'asset.disposal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
            }
        }

    def generate_depreciation_schedule(self):
        """Generate depreciation schedule based on method and parameters"""
        self.ensure_one()

        # Clear existing draft lines
        self.depreciation_line_ids.filtered(lambda l: l.state == 'draft').unlink()

        if self.depreciation_method == 'manual':
            return

        if not self.depreciation_start_date:
            raise ValidationError(_('Please set depreciation start date.'))

        if self.depreciation_method == 'straight':
            self._generate_straight_line_depreciation()
        elif self.depreciation_method == 'declining':
            self._generate_declining_balance_depreciation()
        elif self.depreciation_method == 'double_declining':
            self._generate_double_declining_depreciation()

    def _generate_straight_line_depreciation(self):
        """Generate straight line depreciation schedule"""
        if not self.useful_life:
            raise ValidationError(_('Please set useful life for straight line depreciation.'))

        depreciable_amount = self.purchase_value - self.salvage_value
        annual_depreciation = depreciable_amount / self.useful_life

        for year in range(self.useful_life):
            date = self.depreciation_start_date + relativedelta(years=year+1)

            self.env['asset.depreciation.line'].create({
                'asset_id': self.id,
                'date': date,
                'depreciation_amount': annual_depreciation,
                'state': 'draft',
            })

    def _generate_declining_balance_depreciation(self):
        """Generate declining balance depreciation schedule"""
        if not self.depreciation_rate:
            raise ValidationError(_('Please set depreciation rate for declining balance method.'))

        remaining_value = self.purchase_value
        year = 0

        while remaining_value > self.salvage_value and year < (self.useful_life or 20):
            depreciation_amount = remaining_value * (self.depreciation_rate / 100)

            # Ensure we don't depreciate below salvage value
            if remaining_value - depreciation_amount < self.salvage_value:
                depreciation_amount = remaining_value - self.salvage_value

            if depreciation_amount > 0:
                date = self.depreciation_start_date + relativedelta(years=year+1)
                self.env['asset.depreciation.line'].create({
                    'asset_id': self.id,
                    'date': date,
                    'depreciation_amount': depreciation_amount,
                    'state': 'draft',
                })

                remaining_value -= depreciation_amount

            year += 1

            if year >= 20:  # Safety limit
                break

    def _generate_double_declining_depreciation(self):
        """Generate double declining balance depreciation schedule"""
        if not self.useful_life:
            raise ValidationError(_('Please set useful life for double declining balance method.'))

        rate = (2 / self.useful_life) * 100
        remaining_value = self.purchase_value

        for year in range(self.useful_life):
            depreciation_amount = remaining_value * (rate / 100)

            # Ensure we don't depreciate below salvage value
            if remaining_value - depreciation_amount < self.salvage_value:
                depreciation_amount = remaining_value - self.salvage_value

            if depreciation_amount > 0:
                date = self.depreciation_start_date + relativedelta(years=year+1)
                self.env['asset.depreciation.line'].create({
                    'asset_id': self.id,
                    'date': date,
                    'depreciation_amount': depreciation_amount,
                    'state': 'draft',
                })

                remaining_value -= depreciation_amount

    def action_view_depreciation_lines(self):
        self.ensure_one()
        return {
            'name': f'Depreciation Lines - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.depreciation.line',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }

    def action_view_movements(self):
        self.ensure_one()
        return {
            'name': f'Movements - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.movement',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'name': f'Maintenance - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.maintenance',
            'view_mode': 'tree,calendar,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }

    def action_view_repairs(self):
        self.ensure_one()
        return {
            'name': f'Repairs - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.repair',
            'view_mode': 'tree,calendar,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }


    @api.model
    def cron_post_depreciation(self):
        """Cron job to post due depreciation entries"""
        today = fields.Date.today()

        # Find all depreciation lines due for posting
        lines = self.env['asset.depreciation.line'].search([
            ('state', '=', 'draft'),
            ('date', '<=', today)
        ])

        for line in lines:
            try:
                line.create_depreciation_entry()
            except Exception as e:
                _logger.error(f"Failed to post depreciation for asset {line.asset_id.name}: {str(e)}")
