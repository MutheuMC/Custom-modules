{
    'name': "Timesheet Timer",
    'summary': """Adds timer functionality to timesheet entries.""",
    'description': """
        This module extends the timesheet functionality to include a timer
        button, allowing users to start and stop the timer for a specific task.
    """,
    'author': "Your Name",
    'website': "https://www.odoo.com",
    'category': 'Human Resources/Timesheets',
    'version': '1.0',
    'depends': ['hr_timesheet'],
    'data': [
        'views/timesheet_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'timesheet_timer/static/src/js/timesheet_timer.js',
            'timesheet_timer/static/src/xml/timesheet_timer_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}