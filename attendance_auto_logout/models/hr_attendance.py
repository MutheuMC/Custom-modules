# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time, timedelta
import pytz
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    x_checkout_reason = fields.Char(
        string='Auto Checkout Reason',
        help='Reason for automatic checkout if applicable'
    )

    # ---- helpers -------------------------------------------------------------
    def _param_enabled(self, key, default=True):
        """Return True/False for boolean-like system parameters."""
        val = self.env['ir.config_parameter'].sudo().get_param(
            key, '1' if default else '0'
        )
        return str(val).strip().lower() in ('1', 'true', 'yes', 'y', 'on')

    def _rollover_utc_naive(self):
        """Return yesterday 23:59:59 in configured TZ, converted to naive UTC."""
        param = self.env['ir.config_parameter'].sudo()
        tzname = param.get_param('attendance.rollover_tz', 'Africa/Nairobi')
        try:
            tz = pytz.timezone(tzname)
        except Exception:
            tzname = 'UTC'
            tz = pytz.utc

        now_utc_naive = fields.Datetime.now()
        now_utc = pytz.utc.localize(now_utc_naive)

        today_local = now_utc.astimezone(tz).date()
        yesterday_local = today_local - timedelta(days=1)
        rollover_local = tz.localize(datetime.combine(yesterday_local, time(23, 59, 59)))
        rollover_utc = rollover_local.astimezone(pytz.utc).replace(tzinfo=None)
        return rollover_utc, tzname

    # ---- cron: midnight rollover --------------------------------------------
    @api.model
    def cron_auto_logout_midnight_rollover(self):
        """
        Close any open attendances that cross the previous local midnight.
        Acts as a safety net if stock 'Automatic Check-Out' misses some sessions.
        """
        if not self._param_enabled('attendance.enable_midnight_rollover', True):
            return

        try:
            rollover_utc, tzname = self._rollover_utc_naive()

            open_attendances = self.search([
                ('check_in', '!=', False),
                ('check_out', '=', False),
                ('check_in', '<=', rollover_utc),
            ])

            count = 0
            for att in open_attendances:
                att.write({
                    'check_out': rollover_utc,
                    'x_checkout_reason': f'Auto: midnight rollover ({tzname})',
                })
                count += 1
                _logger.info("Midnight rollover checkout for %s at %s",
                             att.employee_id.display_name, rollover_utc)

            if count:
                _logger.info("Midnight rollover completed for %s record(s).", count)

        except Exception as e:
            _logger.error("Error in midnight rollover auto logout cron: %s", e)
