{
    'name': 'Custom Documents',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Custom Document Management System',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/document_upload_wizard_views.xml',
        'wizard/folder_wizard_views.xml',
        'views/document_views.xml',
        'views/menu.xml',
    ],
    'assets': {
    'web.assets_backend': [
        # your other assets...
        'custom_documents/static/src/views/document_create_redirect.js',
        'custom_documents/static/src/views/folder_create_redirect.js',
        'custom_documents/static/src/js/document_viewer.js',
        'custom_documents/static/src/scss/custom_documents.scss',
            ],
        },
    'controllers': ['controllers/document_controller.py'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
