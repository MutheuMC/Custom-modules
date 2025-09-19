# custom_documents/models/document_folder.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

EMPLOYEE_DEFAULT_CHILDREN = ["Contracts"]          # optional subfolders inside each employee folder
COMPANY_DEFAULT_CHILDREN = ["Finance", "Legal", "Marketing", "Admin", "Inbox"]  # optional top-level under Company


class DocumentFolder(models.Model):
    _name = 'custom.document.folder'
    _description = 'Document Folder'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    # --- Core fields ---
    name = fields.Char('Folder Name', required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True, recursive=True)
    parent_id = fields.Many2one('custom.document.folder', 'Parent Folder', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('custom.document.folder', 'parent_id', 'Child Folders')
    document_ids = fields.One2many('custom.document', 'folder_id', 'Documents')
    document_count = fields.Integer('Document Count', compute='_compute_document_count')
    color = fields.Integer('Color')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user)

    # Link to employee when this is an "employee folder"
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True)

    # Convenience booleans
    is_company_root = fields.Boolean(string="Company Root", default=False, help="Auto-created root folder for the company.")
    is_employees_root = fields.Boolean(string="Employees Root", default=False, help="Auto-created 'Employees – <company>' folder.")

    # ------------------------------------------------------------
    # Computes / constraints
    # ------------------------------------------------------------
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

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folders.'))

    # ------------------------------------------------------------
    # Actions (you already had these — kept as-is)
    # ------------------------------------------------------------
    def action_open_documents(self):
        """Open documents in this folder"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('custom_documents.action_custom_document')
        action.update({
            'name': _('Documents in %s') % self.name,
            'domain': [('folder_id', '=', self.id)],
            'context': {
                **self.env.context,
                'default_folder_id': self.id,
                'search_default_folder_id': self.id,
            }
        })
        return action

    def action_open_folder_tree(self):
        """(Optional) Open subfolder tree view"""
        self.ensure_one()
        return {
            'name': _('Subfolders of %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document.folder',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        }

    def action_view_folder_documents(self):
        """Direct action to view documents in folder"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documents in {self.complete_name}',
            'res_model': 'custom.document',
            'view_mode': 'list',
            'domain': [('folder_id', '=', self.id)],
            'context': {
                'default_folder_id': self.id,
                'create': True,
            },
            'target': 'current',
        }

    # ------------------------------------------------------------
    # Helpers to build the company/employee tree
    # ------------------------------------------------------------
    def _ensure_company_root(self, company):
        """Return the single Company root for a given company (create if missing)."""
        self_sudo = self.sudo()
        root = self_sudo.search([
            ('company_id', '=', company.id),
            ('is_company_root', '=', True),
            ('parent_id', '=', False),
        ], limit=1)
        if not root:
            # keep name short as in the left tree: "Company"
            root = self_sudo.create({
                'name': 'Company',
                'company_id': company.id,
                'user_id': self.env.user.id,
                'is_company_root': True,
            })
        return root

    def _ensure_employees_root(self, company):
        """Return the 'Employees – <Company>' folder (child of Company root)."""
        self_sudo = self.sudo()
        root = self._ensure_company_root(company)
        wanted_name = f"Employees – {company.name}"
        emp_root = self_sudo.search([
            ('parent_id', '=', root.id),
            ('company_id', '=', company.id),
            ('is_employees_root', '=', True),
        ], limit=1)
        if not emp_root:
            emp_root = self_sudo.create({
                'name': wanted_name,
                'parent_id': root.id,
                'company_id': company.id,
                'user_id': self.env.user.id,
                'is_employees_root': True,
            })
        elif emp_root.name != wanted_name:
            emp_root.name = wanted_name
        return emp_root

    def _ensure_default_company_children(self, company):
        """OPTIONAL: Seed a few standard top-level folders under Company."""
        root = self._ensure_company_root(company)
        for name in COMPANY_DEFAULT_CHILDREN:
            exists = self.search([
                ('name', '=', name),
                ('parent_id', '=', root.id),
                ('company_id', '=', company.id),
            ], limit=1)
            if not exists:
                self.create({
                    'name': name,
                    'parent_id': root.id,
                    'company_id': company.id,
                    'user_id': self.env.user.id,
                })

    def _ensure_employee_folder(self, emp):
        """Create/update the folder for a single employee and return it."""
        self_sudo = self.sudo()
        emp_root = self._ensure_employees_root(emp.company_id)
        # One folder per employee per company
        folder = self_sudo.search([
            ('employee_id', '=', emp.id),
            ('company_id', '=', emp.company_id.id),
        ], limit=1)
        # desired display name (avoid falsey strings)
        wanted_name = emp.name or _("Employee %s") % emp.id
        if folder:
            if folder.parent_id.id != emp_root.id:
                folder.parent_id = emp_root.id
            if folder.name != wanted_name:
                folder.name = wanted_name
        else:
            folder = self_sudo.create({
                'name': wanted_name,
                'parent_id': emp_root.id,
                'employee_id': emp.id,
                'company_id': emp.company_id.id,
                'user_id': self.env.user.id,
            })
            # optional child structure under each employee
            for child in EMPLOYEE_DEFAULT_CHILDREN:
                self_sudo.create({
                    'name': child,
                    'parent_id': folder.id,
                    'company_id': emp.company_id.id,
                    'user_id': self.env.user.id,
                })
        return folder


    # ------------------------------------------------------------
    # Small convenience: open the Company root quickly
    # ------------------------------------------------------------
    @api.model
    def action_open_company_root(self):
        """Return an action focused on the Company root tree."""
        root = self._ensure_company_root(self.env.company)
        return {
            'name': _('Company'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document.folder',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', root.id)],
            'context': {'default_parent_id': root.id},
            'target': 'current',
        }
