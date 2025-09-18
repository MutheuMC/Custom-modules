{
    'name': 'Custom Documents',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Custom Document Management System',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/document_upload_wizard_views.xml',
        'views/folder_wizard_views.xml',
        'views/preview_wizard_views.xml',
        'views/actions_wizard_views.xml',      
        'views/rename_wizard_views.xml',        
        'views/properties_wizard_views.xml',  
        'views/document_views.xml',
        'views/document_list_actions.xml',
        'views/menu.xml',
    ],
    'assets': {
    'web.assets_backend': [
        # your other assets...
        'custom_documents/static/src/views/document_create_redirect.js',
        'custom_documents/static/src/views/folder_create_redirect.js',
        'custom_documents/static/src/scss/custom_documents.scss',
        # "custom_documents/static/src/js/selection_buttons.js",
        # "custom_documents/static/src/xml/selection_buttons.xml",
            ],
        },
    'controllers': ['controllers/document_controller.py'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
