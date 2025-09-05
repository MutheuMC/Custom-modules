{
    'name': 'Employee PF Number',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Add PF Number field to employees',
    'description': """
        This module adds a Provident Fund Number (PF Number) field to employee records.
        The field is optional but must be unique if provided.
    """,
    'depends': ['hr'],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}