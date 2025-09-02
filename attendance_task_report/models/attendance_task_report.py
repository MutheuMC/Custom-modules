from odoo import models, fields, tools, api
from datetime import datetime, timedelta

class AttendanceTaskReport(models.Model):
    _name = 'attendance.task.report'
    _description = 'Attendance Task Report'
    _auto = False
    _rec_name = 'employee_id'
    _order = 'attendance_date desc, employee_id'

    # Fields
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    attendance_date = fields.Date(string='Date', readonly=True)
    check_in = fields.Datetime(string='Check In', readonly=True)
    check_out = fields.Datetime(string='Check Out', readonly=True)
    worked_hours = fields.Float(string='Worked Hours', readonly=True)
    tasks = fields.Text(string='Tasks', readonly=True)
    task_descriptions = fields.Text(string='Task Descriptions', readonly=True)
    total_task_hours = fields.Float(string='Total Task Hours', readonly=True)
    project_names = fields.Text(string='Projects', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY att.check_in DESC, att.employee_id) AS id,
                    att.employee_id,
                    emp.department_id,
                    att.check_in::date as attendance_date,
                    att.check_in,
                    att.check_out,
                    EXTRACT(EPOCH FROM (att.check_out - att.check_in))/3600.0 as worked_hours,
                    COALESCE(STRING_AGG(DISTINCT pt.name::text, ', '), 'No tasks logged') as tasks,
                    COALESCE(STRING_AGG(DISTINCT aal.name::text, ' | '), 'No task descriptions') as task_descriptions,
                    COALESCE(SUM(aal.unit_amount), 0) as total_task_hours,
                    COALESCE(STRING_AGG(DISTINCT pp.name::text, ', '), 'No projects') as project_names
                FROM hr_attendance att
                LEFT JOIN hr_employee emp ON emp.id = att.employee_id
                LEFT JOIN account_analytic_line aal 
                    ON aal.employee_id = att.employee_id 
                    AND aal.date = att.check_in::date
                    AND aal.task_id IS NOT NULL
                LEFT JOIN project_task pt ON pt.id = aal.task_id
                LEFT JOIN project_project pp ON pp.id = pt.project_id
                WHERE att.check_in IS NOT NULL
                GROUP BY 
                    att.id, 
                    att.employee_id, 
                    emp.department_id,
                    att.check_in, 
                    att.check_out
                ORDER BY att.check_in DESC
            )
        """ % self._table)