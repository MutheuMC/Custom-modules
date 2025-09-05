from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    pf_no = fields.Char(
        string='PF Number',
        help='Unique Provident Fund Identification Number',
        index=True,
    )
    
    _sql_constraints = [
        ('pf_no_unique', 'UNIQUE(pf_no)', 'PF Number must be unique across all employees!'),
    ]
    
    @api.constrains('pf_no')
    def _check_pf_no(self):
        for employee in self:
            if employee.pf_no:
                # Check if another employee already has this PF number
                if self.search_count([
                    ('pf_no', '=', employee.pf_no),
                    ('id', '!=', employee.id)
                ]) > 0:
                    raise ValidationError(_('This PF Number is already assigned to another employee.'))