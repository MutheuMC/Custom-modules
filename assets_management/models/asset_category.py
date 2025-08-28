# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AssetCategory(models.Model):
    _name = 'asset.category'
    _description = 'Asset Category'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(string='Category Name', required=True, index=True)
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True
    )

    code = fields.Char(string='Category Code')

    parent_id = fields.Many2one(
        'asset.category',
        string='Parent Category',
        index=True,
        ondelete='cascade'
    )

    parent_path = fields.Char(index=True)

    child_id = fields.One2many(
        'asset.category',
        'parent_id',
        string='Child Categories'
    )

    # Default depreciation settings
    depreciation_method = fields.Selection([
        ('straight', 'Straight Line'),
        ('declining', 'Declining Balance'),
        ('double_declining', 'Double Declining Balance'),
        ('manual', 'Manual')
    ], string='Default Depreciation Method', default='straight')

    depreciation_rate = fields.Float(
        string='Default Depreciation Rate (%)',
        help='Annual depreciation rate as percentage'
    )

    useful_life = fields.Integer(
        string='Default Useful Life (Years)',
        help='Expected useful life in years'
    )

    # Default accounts
    account_asset_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        domain=[('account_type', '=', 'asset_fixed')],
        help='Account used for the asset value'
    )

    account_depreciation_id = fields.Many2one(
        'account.account',
        string='Depreciation Account',
        domain=[('account_type', '=', 'asset_fixed')],
        help='Account used for accumulated depreciation'
    )

    account_expense_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        domain=[('account_type', '=', 'expense')],
        help='Account used for depreciation expense'
    )

    # Additional settings
    auto_approve = fields.Boolean(
        string='Auto Approve',
        help='Automatically approve assets in this category'
    )

    require_serial = fields.Boolean(
        string='Require Serial Number',
        help='Require serial number for assets in this category'
    )

    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Needed for "Archived" filter in search view
    active = fields.Boolean(default=True)

    asset_count = fields.Integer(
        compute='_compute_asset_count',
        string='Number of Assets'
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_asset_count(self):
        for category in self:
            category.asset_count = self.env['asset.asset'].search_count([
                ('category_id', 'child_of', category.id)
            ])

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))
        return True

    def action_view_assets(self):
        self.ensure_one()
        action = self.env.ref('assets_management.action_asset').read()[0]
        action['domain'] = [('category_id', 'child_of', self.id)]
        action['context'] = {'default_category_id': self.id}
        return action
