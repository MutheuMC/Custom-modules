{
    'name': 'Attendance Task Report',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Generate attendance reports with associated tasks from timesheets',
    'description': """
        This module allows you to:
        - View attendance records with tasks performed on that day
        - Export attendance data including tasks from timesheets
        - Filter by employee, date range, and department
        - Download reports in Excel format
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'hr_attendance',
        'hr_timesheet',
        'project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/attendance_task_report_views.xml',
        'wizard/export_attendance_tasks_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}