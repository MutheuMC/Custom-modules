# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    attendance_allowed_ips = fields.Char(
        string="Allowed IP Addresses",
        help="Comma-separated list of allowed IPs (e.g., 41.7.9.9, 192.168.1.100)",
        config_parameter="hr_attendance.allowed_ips",
    )
