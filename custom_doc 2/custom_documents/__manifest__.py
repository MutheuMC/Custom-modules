{
    'name': 'Documents  Management File System',
    'version': '18.0.15.13.19',
    'category': 'Document Management',
    'summary': 'Custom Document Management System Systems',
    'depends': ['base', 'web', 'mail', 'hr'],
    'post_init_hook': 'post_init_hook',
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
        # 'views/share_templates.xml'
        'views/share_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'custom_documents/static/src/views/document_create_redirect.js',
            'custom_documents/static/src/views/folder_create_redirect.js',
            'custom_documents/static/src/scss/custom_documents.scss',
            'custom_documents/static/src/xml/custom_document_list_buttons.xml',
            'custom_documents/static/src/scss/custom_docs.scss',
        ],
    },
    'controllers': ['controllers/document_controller.py'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}