# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from datetime import datetime

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # A boolean field to indicate if the timer is currently running for this timesheet entry.
    # This field will be used to toggle the timer buttons and logic.
    is_running = fields.Boolean(
        string='Timer Running',
        default=False,
    )
    
    # A datetime field to store the start time of the timer.
    timer_start_time = fields.Datetime(
        string='Timer Start Time',
    )

    @api.model
    def start_timer(self, timesheet_id):
        """
        Starts the timer for a specific timesheet entry.
        It also stops any other running timers for the current user.
        """
        timesheet = self.browse(timesheet_id)
        if timesheet and timesheet.employee_id.user_id != self.env.user:
            raise exceptions.UserError(_("You can't start a timer for another user's timesheet."))

        # Stop any other running timers for the current user.
        # This ensures only one timer is active at a time.
        self.search([
            ('is_running', '=', True),
            ('employee_id.user_id', '=', self.env.user.id),
        ]).write({'is_running': False})

        # Start the timer for the specified timesheet.
        timesheet.write({
            'is_running': True,
            'timer_start_time': datetime.now(),
        })
        return timesheet.read(['id', 'is_running', 'timer_start_time'])

    @api.model
    def stop_timer(self, timesheet_id):
        """
        Stops the timer for a specific timesheet entry and updates the time spent.
        The elapsed time is added to the existing `unit_amount`.
        """
        timesheet = self.browse(timesheet_id)
        if not timesheet or not timesheet.is_running:
            return False

        # Calculate the time elapsed since the timer started.
        if timesheet.timer_start_time:
            elapsed_time = (datetime.now() - timesheet.timer_start_time).total_seconds() / 3600
            
            timesheet.write({
                'unit_amount': timesheet.unit_amount + elapsed_time,
                'is_running': False,
                'timer_start_time': False, # Reset the timer start time
            })
        
        return timesheet.read(['id', 'is_running', 'unit_amount'])