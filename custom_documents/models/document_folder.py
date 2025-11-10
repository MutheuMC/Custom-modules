from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta

EMPLOYEE_DEFAULT_CHILDREN = ["Contracts"]
COMPANY_DEFAULT_CHILDREN = ["Finance", "Legal", "Marketing", "Admin", "Inbox"]


class DocumentFolder(models.Model):
    _name = 'custom.document.folder'
    _description = 'Document Folder'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # ADDED MAIL TRACKING
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'
    _order = 'sequence, name'

    # --- Core fields ---
    name = fields.Char('Folder Name', required=True, tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True, recursive=True)
    parent_id = fields.Many2one('custom.document.folder', 'Parent Folder', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('custom.document.folder', 'parent_id', 'Child Folders')
    document_ids = fields.One2many('custom.document', 'folder_id', 'Documents')
    virtual_document_ids = fields.Many2many('custom.document', compute='_compute_virtual_documents', string='Virtual Documents')
    all_document_ids = fields.Many2many('custom.document', compute='_compute_all_documents', string='All Documents (Real + Virtual)')
    document_count = fields.Integer('Document Count', compute='_compute_document_count')
    color = fields.Integer('Color')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user, tracking=True)

    # Link to employee when this is an "employee folder"
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True)

    # Convenience booleans
    is_company_root = fields.Boolean(string="Company Root", default=False)
    is_employees_root = fields.Boolean(string="Employees Root", default=False)
    is_virtual = fields.Boolean(string="Virtual Folder", default=False, help="Special folder for My Drive, Recent, etc.")
    virtual_type = fields.Selection([
        ('my_drive', 'My Drive'),
        ('shared', 'Shared with Me'),
        ('recent', 'Recent'),
        ('trash', 'Trash'),
    ], string='Virtual Type')

    # Add sharing fields
    share_ids = fields.One2many(
        'custom.document.folder.share',
        'folder_id',
        string='Shared With'
    )
    
    is_shared = fields.Boolean(
        compute='_compute_is_shared',
        store=True
    )

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

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive folders.'))

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------
    def action_open_documents(self):
        """Open documents in this folder"""
        self.ensure_one()
        
        if self.is_virtual:
            domain = self._get_virtual_folder_domain(self.virtual_type)
            context = {'default_folder_id': False}
            if self.virtual_type == 'trash':
                context['active_test'] = False
        else:
            domain = [('folder_id', '=', self.id)]
            context = {'default_folder_id': self.id}
        
        action = self.env['ir.actions.act_window']._for_xml_id('custom_documents.action_custom_document')
        action.update({
            'name': _('Documents in %s') % self.name,
            'domain': domain,
            'context': {**self.env.context, **context}
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
        
        if self.is_virtual:
            domain = self._get_virtual_folder_domain(self.virtual_type)
            context = {'default_folder_id': False, 'create': True}
            if self.virtual_type == 'trash':
                context['active_test'] = False
        else:
            domain = [('folder_id', '=', self.id)]
            context = {'default_folder_id': self.id, 'create': True}
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documents in {self.complete_name}',
            'res_model': 'custom.document',
            'view_mode': 'list',
            'domain': domain,
            'context': context,
            'target': 'current',
        }

    # ------------------------------------------------------------
    # Helpers to build the company/employee tree
    # ------------------------------------------------------------
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
    def _ensure_company_root(self, company):
        """Ensure the Company root folder exists (wrapper for backward compatibility)"""
        return self._get_company_root(company)

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
        """OPTIONAL: Seed a few standard top-level folders under Company."""
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

    # ------------------------------------------------------------
    # Small convenience: open the Company root quickly
    # ------------------------------------------------------------
    @api.model
    def action_open_company_root(self):
        """Return an action focused on the Company root tree."""
        root = self._get_company_root(self.env.company)
        return {
            'name': _('Company'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document.folder',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', root.id)],
            'context': {'default_parent_id': root.id},
            'target': 'current',
        }
    
    @api.model
    def init_folder_structure(self):
        """Initialize folder structure - called on module installation"""
        company = self.env.company
        
        # Create virtual folders
        self.sudo()._ensure_virtual_folders()
        
        # Create Company root folder
        selfSudo = self.sudo()
        root = selfSudo._get_company_root(company)
        
        # Create default company folders
        selfSudo._ensure_default_company_children(company)
        
        # Create employee folders if hr.employee model exists
        if 'hr.employee' in self.env.registry:
            selfSudo._ensure_employees_root(company)
            employees = self.env['hr.employee'].sudo().search([('company_id', '=', company.id)])
            for emp in employees:
                selfSudo._ensure_employee_folder(emp)
    
    @api.model
    def _ensure_virtual_folders(self, company=None):
        """Create/update virtual folders for special categories (global, not per company)"""
        virtual_folders = [
            ('my_drive', 'My Drive', 15),
            ('shared', 'Shared with me', 20),
            ('recent', 'Recent', 25),
            ('trash', 'Trash', 30),
        ]
        
        for vtype, name, seq in virtual_folders:
            folder = self.sudo().search([
                ('is_virtual', '=', True),
                ('virtual_type', '=', vtype),
            ], limit=1)
            
            if not folder:
                self.sudo().create({
                    'name': name,
                    'company_id': False,
                    'is_virtual': True,
                    'virtual_type': vtype,
                    'sequence': seq,
                })

    @api.depends('is_virtual', 'virtual_type')
    def _compute_virtual_documents(self):
        """Get documents for virtual folders"""
        for folder in self:
            if folder.is_virtual:
                domain = folder._get_virtual_folder_domain(folder.virtual_type)
                docs = self.env['custom.document'].search(domain)
                folder.virtual_document_ids = docs
            else:
                folder.virtual_document_ids = False

    @api.depends('document_ids', 'virtual_document_ids', 'is_virtual')
    def _compute_all_documents(self):
        """Get all documents (real folder or virtual)"""
        for folder in self:
            if folder.is_virtual:
                folder.all_document_ids = folder.virtual_document_ids
            else:
                folder.all_document_ids = folder.document_ids

    @api.depends('document_ids', 'is_virtual', 'virtual_type')
    def _compute_document_count(self):
        for folder in self:
            if folder.is_virtual:
                folder.document_count = self._get_virtual_folder_count(folder.virtual_type)
            else:
                folder.document_count = len(folder.document_ids)
    
    def _get_virtual_folder_count(self, virtual_type):
        """Get document count for virtual folders"""
        domain = self._get_virtual_folder_domain(virtual_type)
        return self.env['custom.document'].search_count(domain)
    
    def _get_virtual_folder_domain(self, virtual_type):
        """Get domain for virtual folder types"""
        uid = self.env.uid
        partner_id = self.env.user.partner_id.id
        seven_days_ago = fields.Datetime.now() - timedelta(days=7)
        
        if virtual_type == 'my_drive':
            return [('user_id', '=', uid), ('active', '=', True)]
        elif virtual_type == 'shared':
            return [
                '|',
                    ('share_line_ids.user_id', '=', uid),
                    ('share_access', 'in', ['internal_view', 'internal_edit']),
                ('user_id', '!=', uid),
                ('active', '=', True)
            ]
        elif virtual_type == 'recent':
            return [('write_date', '>=', seven_days_ago), ('active', '=', True)]
        elif virtual_type == 'trash':
            return [('active', '=', False)]
        elif virtual_type == 'all':
            return [('active', '=', True)]
        return []

    @api.depends('share_ids')
    def _compute_is_shared(self):
        for folder in self:
            folder.is_shared = bool(folder.share_ids)
    
    def action_share_folder(self):
        """Open folder share wizard"""
        self.ensure_one()
        return {
            'name': _('Share Folder: %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.folder.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_folder_id': self.id,
            }
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
    
    def _check_user_has_access(self, user):
        """Check if user has access to this folder (directly or via sharing)"""
        self.ensure_one()
        
        # Owner has access
        if self.user_id.id == user.id:
            return True
        
        # Admin has access
        if user.has_group('base.group_system'):
            return True
        
        # Check if directly shared
        if user.id in self.share_ids.mapped('user_id').ids:
            return True
        
        # Check parent folders (recursive check)
        if self.parent_id:
            return self.parent_id._check_user_has_access(user)
        
        return False