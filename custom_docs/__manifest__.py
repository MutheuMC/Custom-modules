{
    'name': 'Custom Documents Management',
    'version': '1.0.0',
    'category': 'Productivity/Documents',
    'summary': 'Centralized document management system',
    'description': """
        Custom Documents Management System
        ===================================
        This module provides a complete document management system with:
        - Centralized document storage
        - Hierarchical folder structure
        - Tag-based organization
        - Workflow actions
        - Document sharing
        - Activity management
        - Access control
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail',
        'web',
        'portal',
    ],
    'data': [
        'security/documents_security.xml',
        'security/ir.model.access.csv',
        'data/documents_data.xml',
        'views/documents_views.xml',
        'views/documents_folder_views.xml',
        'views/documents_tag_views.xml',
        'views/documents_workflow_views.xml',
        'views/documents_share_views.xml',
        'views/documents_templates.xml',
        'views/documents_menus.xml',
        'wizard/documents_request_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
       'custom_docs/static/src/scss/documents.scss',
            
            # JavaScript Controllers and Views
            'custom_docs/static/src/js/documents_kanban_controller.js',
            'custom_docs/static/src/js/documents_kanban_renderer.js',
            'custom_docs/static/src/js/documents_kanban_view.js',
            
            # XML Templates
            'custom_docs/static/src/xml/documents_kanban_controller.xml',
        ],
          
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}