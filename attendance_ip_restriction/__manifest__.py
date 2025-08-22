{
    "name": "Attendance IP Restriction",
    "version": "1.0",
    "category": "Human Resources",
    "license": "LGPL-3",
    "summary": "Restrict HR attendance check-in/out by allowed IP addresses",
    "depends": ["base", "base_setup", "hr", "hr_attendance"],
    "data": [
        
        "views/res_config_settings.xml",
      
    ],
    "installable": True,
    "application": True,  # so it appears when the Apps filter is on
}
