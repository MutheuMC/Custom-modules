{
    'name': 'Custom Documents',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Custom Document Management System like Enterprise',
    'description': '''
        Custom document management module with:
        - File upload functionality
        - Folder organization
        - URL link documents
        - Modern UI with dropdown actions
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/document_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_documents/static/src/components/**/*.js',
            'custom_documents/static/src/components/**/*.xml',
            'custom_documents/static/src/components/**/*.scss',
            'custom_documents/static/src/js/*.js',
            'custom_documents/static/src/js/*.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}