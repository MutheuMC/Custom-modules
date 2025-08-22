{
    'name': 'Attendance Auto Logout',
    'version': '1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Automatic logout guardrails for HR Attendance',
    'description': """
        Attendance Auto Logout Module
        ==============================
        
        This module adds automatic logout guardrails to HR Attendance:
        - 8-hour maximum session cap
        - Midnight rollover (timezone configurable)
        - Configurable parameters via Settings
        - Automatic checkout reasons tracking
    """,
    'depends': ['hr_attendance', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}