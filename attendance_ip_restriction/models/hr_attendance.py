from odoo import models, api, fields
from odoo.exceptions import ValidationError
from odoo.http import request


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Enforce IP allowlist for attendance creation.
        Uses batch-aware API to avoid deprecation warnings.
        """
        if request and getattr(request, "httprequest", None):
            # Prefer the left-most client IP from X-Forwarded-For if present
            forwarded_for = request.httprequest.environ.get("HTTP_X_FORWARDED_FOR")
            client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else \
                        request.httprequest.environ.get("REMOTE_ADDR")

            allowed_ips = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hr_attendance.allowed_ips", "")
            )
            if allowed_ips:
                allowed_list = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]
                if client_ip not in allowed_list:
                    raise ValidationError(
                        f"Attendance not allowed from IP: {client_ip}. "
                        f"Contact your administrator."
                    )

        # Pass the full list through to the super so batch create works
        return super().create(vals_list)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    attendance_allowed_ips = fields.Char(
        string="Allowed IP Addresses",
        help="Comma-separated list of allowed IPs (e.g., 41.7.9.9, 192.168.1.100)",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        res.update(
            attendance_allowed_ips=(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hr_attendance.allowed_ips", "")
            )
        )
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_attendance.allowed_ips", self.attendance_allowed_ips or ""
        )
