# -*- coding: utf-8 -*-
{
    'name': 'Equipment–Documents Bridge',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Links equipment records with custom documents via folders.',
    'depends': [
        'custom_documents',        # your document module
        'equipment_management',    # ⚠️ replace with your actual equipment module name
    ],
    'data': [
        # No views needed unless you want to show equipment_id in document views
    ],
    'installable': True,
    'application': False,
    'auto_install': True,  # auto-install when both dependencies are present
    'license': 'LGPL-3',
}
