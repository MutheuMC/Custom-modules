from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
from datetime import datetime, timedelta
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

class ExportAttendanceTasksWizard(models.TransientModel):
    _name = 'export.attendance.tasks.wizard'
    _description = 'Export Attendance Tasks Wizard'

    date_from = fields.Date(
        string='Date From', 
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(
        string='Date To', 
        required=True,
        default=fields.Date.today
    )
    employee_ids = fields.Many2many(
        'hr.employee', 
        string='Employees',
        help="Leave empty to include all employees"
    )
    department_ids = fields.Many2many(
        'hr.department', 
        string='Departments',
        help="Leave empty to include all departments"
    )
    format_type = fields.Selection([
        ('xlsx', 'Excel (.xlsx)'),
        ('csv', 'CSV (.csv)')
    ], string='Format', default='xlsx', required=True)

    def action_export(self):
        # Build domain for filtering
        domain = [
            ('attendance_date', '>=', self.date_from),
            ('attendance_date', '<=', self.date_to)
        ]
        
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
            
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))

        # Get data
        records = self.env['attendance.task.report'].search(domain)
        
        if not records:
            raise UserError(_('No records found for the selected criteria.'))

        if self.format_type == 'xlsx':
            return self._export_xlsx(records)
        else:
            return self._export_csv(records)

    def _export_xlsx(self, records):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance Tasks Report')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy'
        })
        
        datetime_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy hh:mm:ss'
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00'
        })

        # Headers
        headers = [
            'Employee', 'Department', 'Date', 'Check In', 'Check Out',
            'Worked Hours', 'Task Hours', 'Projects', 'Tasks', 'Task Descriptions'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Data
        for row, record in enumerate(records, 1):
            worksheet.write(row, 0, record.employee_id.name or '', cell_format)
            worksheet.write(row, 1, record.department_id.name or '', cell_format)
            worksheet.write(row, 2, record.attendance_date, date_format)
            worksheet.write(row, 3, record.check_in, datetime_format)
            worksheet.write(row, 4, record.check_out or '', datetime_format)
            worksheet.write(row, 5, record.worked_hours or 0, number_format)
            worksheet.write(row, 6, record.total_task_hours or 0, number_format)
            worksheet.write(row, 7, record.project_names or '', cell_format)
            worksheet.write(row, 8, record.tasks or '', cell_format)
            worksheet.write(row, 9, record.task_descriptions or '', cell_format)

        # Adjust column widths
        worksheet.set_column(0, 0, 20)  # Employee
        worksheet.set_column(1, 1, 15)  # Department
        worksheet.set_column(2, 2, 12)  # Date
        worksheet.set_column(3, 4, 18)  # Check In/Out
        worksheet.set_column(5, 6, 12)  # Hours
        worksheet.set_column(7, 7, 20)  # Projects
        worksheet.set_column(8, 8, 30)  # Tasks
        worksheet.set_column(9, 9, 40)  # Descriptions

        workbook.close()
        output.seek(0)
        
        filename = f'attendance_tasks_{self.date_from}_{self.date_to}.xlsx'
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=export.attendance.tasks.wizard&id=%s&field=file_data&filename=%s&download=true' % (self.id, filename),
            'target': 'self',
        }

    def _export_csv(self, records):
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Employee', 'Department', 'Date', 'Check In', 'Check Out',
            'Worked Hours', 'Task Hours', 'Projects', 'Tasks', 'Task Descriptions'
        ])
        
        # Data
        for record in records:
            writer.writerow([
                record.employee_id.name or '',
                record.department_id.name or '',
                record.attendance_date.strftime('%Y-%m-%d') if record.attendance_date else '',
                record.check_in.strftime('%Y-%m-%d %H:%M:%S') if record.check_in else '',
                record.check_out.strftime('%Y-%m-%d %H:%M:%S') if record.check_out else '',
                record.worked_hours or 0,
                record.total_task_hours or 0,
                record.project_names or '',
                record.tasks or '',
                record.task_descriptions or ''
            ])
        
        filename = f'attendance_tasks_{self.date_from}_{self.date_to}.csv'
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=export.attendance.tasks.wizard&id={self.id}&field=file_data&filename={filename}&download=true',
            'target': 'self',
        }

    file_data = fields.Binary('File', readonly=True)
    filename = fields.Char('Filename', readonly=True)
