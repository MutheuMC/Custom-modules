{
    'name': 'Custom Documents',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Manage documents with folders and tags',
    'description': """
        Custom document management system for Odoo 18
        - Document management with folders and tags
        - Access control permissions
        - Document sharing and collaboration
    """,
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'depends': ['base', 'mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/document_security.xml',
        'views/folder_views.xml',
        'views/tag_views.xml',
        'views/document_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_documents/static/src/css/document_style.css',
            'custom_documents/static/src/js/document_kanban.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}