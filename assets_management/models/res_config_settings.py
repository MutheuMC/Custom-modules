from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Asset Management Settings
    asset_auto_approve = fields.Boolean(
        string='Auto Approve Assets',
        config_parameter='assets_management.auto_approve',
        help='Automatically approve newly created assets'
    )
    
    asset_generate_code = fields.Boolean(
        string='Auto Generate Asset Code',
        config_parameter='assets_management.generate_code',
        default=True,
        help='Automatically generate asset codes'
    )
    
    asset_code_prefix = fields.Char(
        string='Asset Code Prefix',
        config_parameter='assets_management.code_prefix',
        default='AST',
        help='Prefix for auto-generated asset codes'
    )
    
    # Depreciation Settings
    depreciation_auto_post = fields.Boolean(
        string='Auto Post Depreciation',
        config_parameter='assets_management.auto_post_depreciation',
        help='Automatically post depreciation entries'
    )
    
    depreciation_journal_id = fields.Many2one(
        'account.journal',
        string='Depreciation Journal',
        config_parameter='assets_management.depreciation_journal_id',
        domain=[('type', '=', 'general')]
    )
    
    # Maintenance Settings
    maintenance_auto_create = fields.Boolean(
        string='Auto Create Recurring Maintenance',
        config_parameter='assets_management.auto_create_maintenance',
        help='Automatically create recurring maintenance tasks'
    )
    
    maintenance_advance_days = fields.Integer(
        string='Create Maintenance Days in Advance',
        config_parameter='assets_management.maintenance_advance_days',
        default=7,
        help='Number of days in advance to create maintenance tasks'
    )
    
    # Notification Settings
    notify_warranty_expiry = fields.Boolean(
        string='Notify Warranty Expiry',
        config_parameter='assets_management.notify_warranty_expiry',
        help='Send notifications for warranty expiry'
    )
    
    warranty_expiry_days = fields.Integer(
        string='Warranty Expiry Warning Days',
        config_parameter='assets_management.warranty_expiry_days',
        default=30,
        help='Days before warranty expiry to send notification'
    )
    
    notify_insurance_expiry = fields.Boolean(
        string='Notify Insurance Expiry',
        config_parameter='assets_management.notify_insurance_expiry',
        help='Send notifications for insurance expiry'
    )
    
    insurance_expiry_days = fields.Integer(
        string='Insurance Expiry Warning Days',
        config_parameter='assets_management.insurance_expiry_days',
        default=30,
        help='Days before insurance expiry to send notification'
    )