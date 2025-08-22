# -*- coding: utf-8 -*-
from odoo import models, fields, api
import pytz


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_rollover_tz = fields.Selection(
        selection='_get_timezone_selection',
        string='Rollover Timezone',
        default='Africa/Nairobi',
        config_parameter='attendance.rollover_tz',
        help='Timezone used to compute the 23:59:59 cutoff for the midnight rollover.'
    )

    attendance_enable_midnight_rollover = fields.Boolean(
        string='Enable Midnight Rollover',
        default=True,
        config_parameter='attendance.enable_midnight_rollover',
        help='When enabled, a daily scheduled action force-checks out open attendances at local midnight.'
    )

    @api.model
    def _get_timezone_selection(self):
        """All available timezones."""
        # Keep order stable for UX
        return [(tz, tz) for tz in pytz.all_timezones]
