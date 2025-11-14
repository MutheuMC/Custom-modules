from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentReferenceWizard(models.TransientModel):
    _name = 'custom.document.reference.wizard'
    _description = 'Document Reference Number Wizard'

    document_id = fields.Many2one(
        'custom.document',
        string='Document',
        required=True,
        readonly=True,
    )

    department = fields.Selection([
        ('hr', 'Human Resource'),
        ('proc', 'Procurement'),
        ('vc', 'Vice Chancellor'),
        ('dvaf', 'DVC A&F'),
    ], string='Department', required=True)

    def _get_department_code(self):
        self.ensure_one()
        mapping = {
            'hr': 'HR',
            'proc': 'PROC',
            'vc': 'VC',
            'dvaf': 'DVA&F',
        }
        return mapping.get(self.department, 'GEN')

    def action_generate_reference(self):
        """Generate and assign reference number to the document."""
        self.ensure_one()
        if not self.document_id:
            raise UserError(_("No document selected."))

        Document = self.env['custom.document']

        # Current year (YY)
        today = fields.Date.context_today(self)
        year_full = today.year
        year_short = str(year_full)[-2:]

        dept_code = self._get_department_code()

        # Find last sequence for this department + year
        last_doc = Document.search([
            ('reference_department', '=', self.department),
            ('reference_year', '=', year_short),
        ], order='reference_seq desc', limit=1)

        next_seq = (last_doc.reference_seq or 0) + 1
        seq_str = f"{next_seq:03d}"  # 001, 002, ...

        # Build reference like: DEKUT| SIEMENS|HR|001|25
        ref = f"DEKUT| SIEMENS|{dept_code}|{seq_str}|{year_short}"

        self.document_id.write({
            'reference_department': self.department,
            'reference_seq': next_seq,
            'reference_year': year_short,
            'reference_number': ref,
        })

        return {'type': 'ir.actions.act_window_close'}
