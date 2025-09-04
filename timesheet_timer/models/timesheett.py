# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    is_timer_running = fields.Boolean(
        string="Timer Running",
        default=False,
        help="Indicates if the timer is currently running for this timesheet entry.",
    )
    timer_start = fields.Datetime(
        string="Timer Start Time",
        help="Stores when the timer was started.",
    )
    timer_pause = fields.Float(
        string="Timer Accumulated (hours)",
        default=0.0,
        help="Accumulated time in hours when the timer was started or last paused.",
    )

    # Record method (not a model method)
    def action_timer_start(self):
        """Start the timer for this timesheet line."""
        self.ensure_one()
        user = self.env.user

        # Permissions: owner or approver may operate
        if self.create_uid.id != user.id and not user.has_group(
            "hr_timesheet.group_hr_timesheet_approver"
        ):
            raise UserError(_("You can only start the timer for your own timesheet entries."))

        # Stop any other running timer for the current user
        running = self.search([
            ("is_timer_running", "=", True),
            ("create_uid", "=", user.id),
            ("id", "!=", self.id),
        ])
        if running:
            running.action_timer_stop()

        # Start this timer; stash current unit_amount into timer_pause
        self.write({
            "is_timer_running": True,
            "timer_start": fields.Datetime.now(),
            "timer_pause": self.unit_amount or 0.0,
        })
        return True

    # Record method (not a model method)
    def action_timer_stop(self):
        """Stop the timer and write elapsed time to unit_amount (hours)."""
        self.ensure_one()

        if not self.is_timer_running:
            return False

        elapsed_hours = 0.0
        if self.timer_start:
            delta = fields.Datetime.now() - self.timer_start
            elapsed_hours = delta.total_seconds() / 3600.0

        total_hours = (self.timer_pause or 0.0) + elapsed_hours
        self.write({
            "unit_amount": total_hours,
            "is_timer_running": False,
            "timer_start": False,
            "timer_pause": 0.0,
        })
        return True

    @api.model
    def get_running_timer(self):
        """For convenience: return the current user's running timer (if any)."""
        rec = self.search([
            ("is_timer_running", "=", True),
            ("create_uid", "=", self.env.user.id)
        ], limit=1)
        
        if not rec:
            return False
            
        return {
            "id": rec.id,
            "timer_start": rec.timer_start,
            "timer_pause": rec.timer_pause,
            "name": rec.name or "",
            "project_id": rec.project_id.name if rec.project_id else "",
            "task_id": rec.task_id.name if rec.task_id else "",
        }

    def compute_current_time(self):
        """Compute current elapsed time for display (hours)."""
        self.ensure_one()
        if self.is_timer_running and self.timer_start:
            delta = fields.Datetime.now() - self.timer_start
            return (self.timer_pause or 0.0) + (delta.total_seconds() / 3600.0)
        return self.unit_amount or 0.0