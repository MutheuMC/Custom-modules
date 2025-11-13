# -*- coding: utf-8 -*-
{
    'name': 'Equipment–Documents Bridge',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Auto-link equipment items with documents via folders.',
    'depends': [
        'custom_documents',        # your document module
        'equipment_management',    # TODO: replace with actual equipment module name
    ],
    'data': [
        'views/document_equipment_bridge_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,  # auto-installs when both deps are installed
    'license': 'LGPL-3',
}
