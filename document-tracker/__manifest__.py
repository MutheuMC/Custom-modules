{
    'name': 'Document Tracking System',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Track document movement between offices',
    'description': """
        Document Tracking System
        ========================
        This module helps track physical documents as they move between different offices.
        
        Features:
        - Document registration with upload/scan options
        - Movement tracking between offices
        - Complete audit trail
        - Dashboard and reporting
        - Notification system
    """,
    'author': 'Your Organization',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/document_tracking_security.xml',
        'security/ir.model.access.csv',
        'data/document_data.xml',
        'views/document_tracker_views.xml',
        'views/office_location_views.xml',
        'views/document_movement_views.xml',
        'views/menu_views.xml',
        'wizard/document_movement_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}