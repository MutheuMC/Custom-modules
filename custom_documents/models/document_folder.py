from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

EMPLOYEE_DEFAULT_CHILDREN = ["Contracts"]
COMPANY_DEFAULT_CHILDREN = ["Projects", "Equipment", "Finance", "Marketing", "Admin", "Inbox"]


class DocumentFolder(models.Model):
    _name = 'custom.document.folder'
    _description = 'Document Folder'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'
    _order = 'sequence, name'

    # --- Core fields ---
    name = fields.Char('Folder Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True, recursive=True)
    parent_id = fields.Many2one('custom.document.folder', 'Parent Folder', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('custom.document.folder', 'parent_id', 'Child Folders')
    document_ids = fields.One2many('custom.document', 'folder_id', 'Documents')
    document_count = fields.Integer('Document Count', compute='_compute_document_count')
    color = fields.Integer('Color')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True)
    is_starred = fields.Boolean('Starred', default=False)

    # Convenience booleans
    is_company_root = fields.Boolean(string="Company Root", default=False)
    is_employees_root = fields.Boolean(string="Employees Root", default=False)

    # Sharing fields
    share_ids = fields.One2many('custom.document.folder.share', 'folder_id', string='Shared With')
    is_shared = fields.Boolean(compute='_compute_is_shared', store=True)

    @api.constrains('is_company_root', 'company_id')
    def _constr_unique_company_root(self):
        for rec in self.filtered('is_company_root'):
            exists = self.search_count([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('is_company_root', '=', True),
            ])
            if exists:
                raise ValidationError(_('Only one Company root folder per company is allowed!'))

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = '%s / %s' % (folder.parent_id.complete_name, folder.name)
            else:
                folder.complete_name = folder.name

    @api.depends('document_ids')
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)

    @api.depends('share_ids')
    def _compute_is_shared(self):
        for folder in self:
            folder.is_shared = bool(folder.share_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive folders.'))

    def action_toggle_star(self):
        for rec in self:
            rec.is_starred = not rec.is_starred
        return False

    def action_view_folder_documents(self):
        """Direct action to view documents in folder"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documents in {self.complete_name}',
            'res_model': 'custom.document',
            'view_mode': 'list',
            'domain': [('folder_id', '=', self.id)],
            'context': {'default_folder_id': self.id, 'create': True},
            'target': 'current',
        }

    def action_share_folder(self):
        """Open folder share wizard"""
        self.ensure_one()
        return {
            'name': _('Share Folder: %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.folder.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_folder_id': self.id},
        }

    def action_menu_rename(self):
        """Open rename wizard for folder"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rename Folder'),
            'res_model': 'custom.document.folder.rename.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_folder_id': self.id,
                'default_new_name': self.name,
            },
        }

    # Helper methods for company/employee structure
    @api.model
    def _get_company_root(self, company):
        """Return the single Company root for a given company (create if missing)."""
        root = self.sudo().search([
            ('company_id', '=', company.id),
            ('is_company_root', '=', True),
            ('parent_id', '=', False),
        ], limit=1)
        if not root:
            root = self.sudo().create({
                'name': 'Company',
                'company_id': company.id,
                'user_id': self.env.user.id,
                'is_company_root': True,
                'sequence': 5,
            })
        return root

    @api.model
    def _ensure_employees_root(self, company):
        """Return the 'Employees – <Company>' folder (child of Company root)."""
        root = self._get_company_root(company)
        wanted_name = f"Employees - {company.name}"
        emp_root = self.sudo().search([
            ('parent_id', '=', root.id),
            ('company_id', '=', company.id),
            ('is_employees_root', '=', True),
        ], limit=1)
        if not emp_root:
            emp_root = self.sudo().create({
                'name': wanted_name,
                'parent_id': root.id,
                'company_id': company.id,
                'user_id': self.env.user.id,
                'is_employees_root': True,
            })
        elif emp_root.name != wanted_name:
            emp_root.name = wanted_name
        return emp_root

    @api.model
    def _ensure_default_company_children(self, company):
        """Seed standard top-level folders under Company."""
        root = self._get_company_root(company)
        for name in COMPANY_DEFAULT_CHILDREN:
            exists = self.sudo().search([
                ('name', '=', name),
                ('parent_id', '=', root.id),
                ('company_id', '=', company.id),
            ], limit=1)
            if not exists:
                self.sudo().create({
                    'name': name,
                    'parent_id': root.id,
                    'company_id': company.id,
                    'user_id': self.env.user.id,
                })

    @api.model
    def _ensure_employee_folder(self, emp):
        """Create/update the folder for a single employee and return it."""
        emp_root = self._ensure_employees_root(emp.company_id)
        folder = self.sudo().search([
            ('employee_id', '=', emp.id),
            ('company_id', '=', emp.company_id.id),
        ], limit=1)
        wanted_name = emp.name or _("Employee %s") % emp.id
        if folder:
            if folder.parent_id.id != emp_root.id:
                folder.parent_id = emp_root.id
            if folder.name != wanted_name:
                folder.name = wanted_name
        else:
            folder = self.sudo().create({
                'name': wanted_name,
                'parent_id': emp_root.id,
                'employee_id': emp.id,
                'company_id': emp.company_id.id,
                'user_id': self.env.user.id,
            })
            for child in EMPLOYEE_DEFAULT_CHILDREN:
                self.sudo().create({
                    'name': child,
                    'parent_id': folder.id,
                    'company_id': emp.company_id.id,
                    'user_id': self.env.user.id,
                })
        return folder