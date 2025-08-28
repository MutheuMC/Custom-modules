{
    'name': 'Assets Management',
    'version': '1.0.0',
    'category': 'Accounting/Assets',
    'summary': 'Complete Asset Management System with Depreciation, Maintenance, and Tracking',
    'description': """
        Assets Management Module
        ========================
        
        Comprehensive asset management system similar to ERPNext featuring:
        
        * Asset Registration & Tracking
        * Multiple Depreciation Methods (Straight Line, Declining Balance, Double Declining)
        * Asset Categories with default settings
        * Asset Movement & Transfer tracking
        * Maintenance Scheduling & Tracking
        * Repair Management
        * Asset Disposal & Write-offs
        * Barcode/QR Code support
        * Comprehensive Reporting
        * Integration with Accounting
        
        Key Features:
        -------------
        - Complete Asset Lifecycle Management
        - Automatic Depreciation Calculation
        - Maintenance Schedule Automation
        - Asset Location Tracking
        - Document Management
        - Multi-company Support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'account',
        'hr',
        'stock',
        'mail',
        'product',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence_data.xml',
        'data/asset_data.xml',
        'data/ir_cron_data.xml',
        
        # Views
        'views/asset_category_views.xml',
        'views/asset_views.xml',
        'views/asset_depreciation_views.xml',
        'views/asset_movement_views.xml',
        'views/asset_maintenance_views.xml',
        'views/asset_repair_views.xml',
        'views/asset_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        
        # Wizard
        'wizard/asset_disposal_wizard_views.xml',
        
        # Reports
        'reports/asset_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'assets_management/static/src/js/asset_dashboard.js',
        ],
    },
}