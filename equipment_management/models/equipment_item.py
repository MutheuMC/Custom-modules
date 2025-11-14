# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import io

try:
    import qrcode
except ImportError:
    qrcode = None


class EquipmentItem(models.Model):
    _name = 'equipment.item'
    _description = 'Lab Equipment Item'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'name, id'

    # ------------- Basic -------------
    name = fields.Char(string='Equipment Name', required=True, tracking=True)
    barcode = fields.Char(string='Barcode/QR Code', copy=False, tracking=True,
                          help='Unique barcode for scanning. Auto-generated if left blank.')
    serial_number = fields.Char(string='Serial Number', copy=False, tracking=True)
    asset_tag = fields.Char(string='Asset Tag', copy=False, tracking=True)
    model_number = fields.Char(string='Model Number', tracking=True)

    # ------------- Categorization -------------
    category_id = fields.Many2one('equipment.category', string='Category',
                                  required=True, tracking=True, ondelete='restrict')

    # ------------- Location & Holder -------------
    location_id = fields.Many2one(
        'equipment.location', string='Current Location', required=True, tracking=True,
        default=lambda self: self._default_main_store_id(),
        help='Physical location of the equipment'
    )

    holder_type = fields.Selection([
        ('none', 'None'),
        ('employee', 'Employee'),
        ('department', 'Department'),
        ('other', 'Other'),
    ], string='Holder Type', default='none', required=True, tracking=True)

    employee_id = fields.Many2one(
        'res.partner', string='Employee',
        domain="[('is_company','=',False)]", tracking=True)

    department_id = fields.Many2one(
        'res.partner', string='Department/Unit',
        domain="[('is_company','=',True)]", tracking=True)

    custodian_partner_id = fields.Many2one(
        'res.partner', string='External Custodian', tracking=True)

    assigned_date = fields.Date(string='Assigned Date', tracking=True)
    custodian_id = fields.Many2one('res.users', string='Current Custodian', tracking=True,
                                   help='Person currently responsible due to a loan')

    # ------------- Status -------------
    state = fields.Selection([
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
        ('lost', 'Lost/Missing'),
    ], string='Status', default='available', required=True, tracking=True)

    # ------------- Equipment Details -------------
    manufacturer = fields.Char(tracking=True)
    model = fields.Char(string='Model', tracking=True)
    model_year = fields.Integer(string='Model Year')
    specifications = fields.Text(string='Technical Specifications')

    # ------------- Purchase -------------
    purchase_date = fields.Date(string='Purchase Date', tracking=True)
    purchase_value = fields.Monetary(string='Purchase Value', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain=[('supplier_rank', '>', 0)])
    purchase_order_ref = fields.Char(string='PO Reference')

    # ------------- Warranty -------------
    warranty_start_date = fields.Date(string='Warranty Start Date')
    warranty_end_date = fields.Date(string='Warranty End Date')
    warranty_active = fields.Boolean(string='Under Warranty',
                                     compute='_compute_warranty_active', store=True)

    # ------------- Physical -------------
    weight = fields.Float(string='Weight (kg)')
    dimensions = fields.Char(string='Dimensions (L×W×H)')
    color = fields.Char(string='Color')

    # ------------- Condition -------------
    condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], string='Condition', default='good', tracking=True)
    condition_notes = fields.Text(string='Condition Notes')

    # ------------- DOCUMENT INTEGRATION -------------
    equipment_folder_id = fields.Many2one(
        'custom.document.folder',
        string='Equipment Folder',
        help='Dedicated folder for this equipment documents',
        copy=False,
        readonly=True
    )
    
    # document_ids = fields.One2many(
    #     'custom.document',
    #     'equipment_id',
    #     string='Documents'
    # )
    
    document_count = fields.Integer(
        string='Documents',
        compute='_compute_document_count'
    )

    # ------------- Media / Relations -------------
    qr_code_image = fields.Binary(string='QR Code', compute='_compute_qr_code_image', store=False, attachment=False)
    loan_ids = fields.One2many('equipment.loan', 'equipment_id', string='Loan History')
    maintenance_ids = fields.One2many('equipment.maintenance', 'equipment_id', string='Maintenance Records')
    reservation_ids = fields.Many2many(
        'equipment.reservation',
        'equipment_reservation_rel',
        'equipment_id',
        'reservation_id',
        string='Reservations'
    )

    # ------------- Stats -------------
    loan_count = fields.Integer(string='Total Loans', compute='_compute_loan_count')
    active_loan_id = fields.Many2one('equipment.loan', string='Active Loan', compute='_compute_active_loan', store=False)
    next_maintenance_date = fields.Date(string='Next Maintenance', compute='_compute_next_maintenance', store=True)

    # ------------- Misc -------------
    notes = fields.Html(string='Notes')
    responsible_id = fields.Many2one('res.users', string='Responsible Person', tracking=True)
    active = fields.Boolean(default=True)
    attachment_count = fields.Integer(string='Attachments', compute='_compute_attachment_count')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    assignment_ids = fields.One2many('equipment.assignment', 'equipment_id', string='Assignment History')
    assignment_count = fields.Integer(compute='_compute_assignment_count')

    _sql_constraints = [
        ('barcode_company_unique', 'UNIQUE(barcode, company_id)', 'Barcode must be unique per company!'),
        ('serial_number_unique', 'UNIQUE(serial_number, company_id)', 'Serial number must be unique per company!'),
    ]

    # ---------- Defaults / Helpers ----------
    def _default_main_store_id(self):
        ms = self.env.ref('equipment_management.location_main_store', raise_if_not_found=False)
        return ms.id if ms else False

    def _is_main_store(self):
        ms = self.env.ref('equipment_management.location_main_store', raise_if_not_found=False)
        return bool(ms and self.location_id and self.location_id.id == ms.id)

    # ---------- DOCUMENT FOLDER MANAGEMENT ----------
    @api.model
    def _ensure_equipment_root_folder(self, company):
        """Ensure Equipment root folder exists under Company root"""
        FolderModel = self.env['custom.document.folder']
        company_root = FolderModel._get_company_root(company)
        
        equipment_root = FolderModel.sudo().search([
            ('name', '=', 'Equipment'),
            ('parent_id', '=', company_root.id),
            ('company_id', '=', company.id),
        ], limit=1)
        
        if not equipment_root:
            equipment_root = FolderModel.sudo().create({
                'name': 'Equipment',
                'parent_id': company_root.id,
                'company_id': company.id,
                'user_id': self.env.user.id,
                'sequence': 15,
            })
        
        return equipment_root

    def _ensure_category_folder(self, category, equipment_root):
        """Ensure category folder exists under Equipment root"""
        FolderModel = self.env['custom.document.folder']
        
        category_folder = FolderModel.sudo().search([
            ('name', '=', category.name),
            ('parent_id', '=', equipment_root.id),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        
        if not category_folder:
            category_folder = FolderModel.sudo().create({
                'name': category.name,
                'parent_id': equipment_root.id,
                'company_id': self.company_id.id,
                'user_id': self.env.user.id,
            })
        
        return category_folder

    def _create_equipment_folder(self):
        """Create dedicated folder for this equipment item"""
        self.ensure_one()
        
        if self.equipment_folder_id:
            return self.equipment_folder_id
        
        FolderModel = self.env['custom.document.folder']
        
        # Build folder structure: Company/Equipment/<Category>/<Equipment Name>
        equipment_root = self._ensure_equipment_root_folder(self.company_id)
        category_folder = self._ensure_category_folder(self.category_id, equipment_root)
        
        # Create equipment-specific folder
        folder_name = f"{self.name} ({self.barcode or self.serial_number or self.id})"
        
        equipment_folder = FolderModel.sudo().create({
            'name': folder_name,
            'parent_id': category_folder.id,
            'company_id': self.company_id.id,
            'user_id': self.env.user.id,
        })
        
        # Create subfolders for organization
        subfolder_names = [
            'Purchase Documents',
            'Warranty & Certificates',
           
        ]
        
        for subfolder_name in subfolder_names:
            FolderModel.sudo().create({
                'name': subfolder_name,
                'parent_id': equipment_folder.id,
                'company_id': self.company_id.id,
                'user_id': self.env.user.id,
            })
        
        self.sudo().write({'equipment_folder_id': equipment_folder.id})
        return equipment_folder

    def _update_folder_name(self):
        """Update folder name when equipment name or barcode changes"""
        self.ensure_one()
        if self.equipment_folder_id:
            new_name = f"{self.name} ({self.barcode or self.serial_number or self.id})"
            if self.equipment_folder_id.name != new_name:
                self.equipment_folder_id.sudo().write({'name': new_name})

    # ---------- Create / Write ----------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'barcode' in vals and not (vals['barcode'] or '').strip():
                vals['barcode'] = False

            if not vals.get('barcode'):
                company_id = vals.get('company_id') or self.env.company.id
                seq_env = self.env['ir.sequence'].with_context(force_company=company_id)

                for _ in range(10):
                    candidate = seq_env.next_by_code('equipment.item')
                    if not candidate:
                        break
                    exists = self.search_count([
                        ('company_id', '=', company_id),
                        ('barcode', '=', candidate),
                    ])
                    if not exists:
                        vals['barcode'] = candidate
                        break
                if not vals.get('barcode'):
                    raise UserError(_('Could not generate a unique barcode.'))

            vals.setdefault('holder_type', 'none')
            for f in ('employee_id','department_id','custodian_partner_id','assigned_date'):
                vals.setdefault(f, False)
            if not vals.get('location_id'):
                ms = self._default_main_store_id()
                if ms:
                    vals['location_id'] = ms
        
        records = super().create(vals_list)
        
        # Create folder for each new equipment item
        for record in records:
            record._create_equipment_folder()
        
        return records

    def write(self, vals):
        if 'barcode' in vals and not (vals['barcode'] or '').strip():
            vals['barcode'] = False

        result = super().write(vals)

        # Update folder names if equipment name/barcode changed
        if 'name' in vals or 'barcode' in vals or 'serial_number' in vals:
            for rec in self:
                rec._update_folder_name()

        # Auto-cohere state on assignment changes
        blocking = {'borrowed', 'maintenance', 'retired', 'lost', 'reserved'}

        if any(k in vals for k in ('holder_type', 'employee_id', 'department_id', 'custodian_partner_id')):
            for rec in self:
                if rec.state not in blocking:
                    if rec.holder_type == 'none':
                        if rec.state != 'available':
                            super(EquipmentItem, rec).write({'state': 'available'})
                    else:
                        if rec.state != 'assigned':
                            super(EquipmentItem, rec).write({'state': 'assigned'})

        if vals.get('state') == 'available' and 'custodian_id' not in vals:
            for rec in self:
                if rec.custodian_id:
                    super(EquipmentItem, rec).write({'custodian_id': False})

        return result

    # ---------- Onchange ----------
    @api.onchange('holder_type')
    def _onchange_holder_type(self):
        if self.holder_type == 'employee':
            self.department_id = False
            self.custodian_partner_id = False
        elif self.holder_type == 'department':
            self.employee_id = False
            self.custodian_partner_id = False
        elif self.holder_type == 'other':
            self.employee_id = False
            self.department_id = False
        else:
            self.employee_id = False
            self.department_id = False
            self.custodian_partner_id = False
            self.assigned_date = False

    # ---------- Constraints ----------
    @api.constrains('location_id', 'holder_type', 'employee_id', 'department_id', 'custodian_partner_id', 'assigned_date')
    def _check_assignment_rules(self):
        ms = self.env.ref('equipment_management.location_main_store', raise_if_not_found=False)
        ms_id = ms.id if ms else False

        for rec in self:
            if rec.location_id and rec.location_id.id == ms_id:
                if rec.holder_type != 'none' or rec.employee_id or rec.department_id or rec.custodian_partner_id or rec.assigned_date:
                    raise ValidationError(_('Items in Main Store cannot be assigned.'))

            if rec.holder_type != 'none':
                if rec.location_id and rec.location_id.id == ms_id:
                    raise ValidationError(_('Assigned items cannot remain in Main Store.'))
                if not rec.assigned_date:
                    raise ValidationError(_('Assigned Date is required when the item has a holder.'))

                cnt = int(bool(rec.employee_id)) + int(bool(rec.department_id)) + int(bool(rec.custodian_partner_id))
                if cnt != 1:
                    raise ValidationError(_('Exactly one holder must be set.'))

                if rec.holder_type == 'employee' and not rec.employee_id:
                    raise ValidationError(_('Please set Employee.'))
                if rec.holder_type == 'department' and not rec.department_id:
                    raise ValidationError(_('Please set Department/Unit.'))
                if rec.holder_type == 'other' and not rec.custodian_partner_id:
                    raise ValidationError(_('Please set External Custodian.'))

    @api.constrains('barcode')
    def _check_barcode(self):
        for item in self:
            if item.barcode and len(item.barcode) < 3:
                raise ValidationError(_('Barcode must be at least 3 characters long.'))

    # ---------- Computes ----------
    @api.depends('barcode')
    def _compute_qr_code_image(self):
        for item in self:
            if item.barcode and qrcode:
                try:
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                    qr.add_data(item.barcode)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    item.qr_code_image = base64.b64encode(buffer.getvalue())
                except Exception:
                    item.qr_code_image = False
            else:
                item.qr_code_image = False

    @api.depends('warranty_end_date')
    def _compute_warranty_active(self):
        today = fields.Date.today()
        for item in self:
            item.warranty_active = bool(item.warranty_end_date and item.warranty_end_date >= today)

    @api.depends('loan_ids')
    def _compute_loan_count(self):
        for item in self:
            item.loan_count = len(item.loan_ids)

    def _compute_active_loan(self):
        for item in self:
            active_loan = self.env['equipment.loan'].search([
                ('equipment_id', '=', item.id),
                ('state', 'in', ['approved', 'issued'])
            ], limit=1)
            item.active_loan_id = active_loan.id if active_loan else False

    @api.depends('maintenance_ids.scheduled_date', 'maintenance_ids.state')
    def _compute_next_maintenance(self):
        for item in self:
            next_maintenance = self.env['equipment.maintenance'].search([
                ('equipment_id', '=', item.id),
                ('state', '=', 'scheduled'),
                ('scheduled_date', '>=', fields.Date.today())
            ], order='scheduled_date asc', limit=1)
            item.next_maintenance_date = next_maintenance.scheduled_date if next_maintenance else False

    @api.depends('equipment_folder_id')
    def _compute_document_count(self):
        """Count documents in equipment folder and subfolders"""
        for item in self:
            if item.equipment_folder_id:
                # Count all documents in folder and subfolders
                count = self.env['custom.document'].search_count([
                    ('folder_id', 'child_of', item.equipment_folder_id.id)
                ])
                item.document_count = count
            else:
                item.document_count = 0

    def _compute_attachment_count(self):
        """Keep legacy attachment count for backward compatibility"""
        for item in self:
            item.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'equipment.item'),
                ('res_id', '=', item.id)
            ])
    
    def _compute_assignment_count(self):
        for item in self:
            item.assignment_count = len(item.assignment_ids)

    # ---------- Actions ----------
    def action_view_documents(self):
        """View all documents for this equipment in folder structure"""
        self.ensure_one()
        
        if not self.equipment_folder_id:
            self._create_equipment_folder()
        
        return {
            'name': _('Documents - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document',
            'view_mode': 'list,form',
            'domain': [('folder_id', 'child_of', self.equipment_folder_id.id)],
            'context': {
                'default_folder_id': self.equipment_folder_id.id,
                'default_equipment_id': self.id,
                'equipment_mode': True,
            },
        }

    def action_upload_document(self):
        """Quick upload document to equipment folder"""
        self.ensure_one()
        
        if not self.equipment_folder_id:
            self._create_equipment_folder()
        
        # Get "Purchase Documents" subfolder by default
        purchase_folder = self.env['custom.document.folder'].sudo().search([
            ('name', '=', 'Purchase Documents'),
            ('parent_id', '=', self.equipment_folder_id.id),
        ], limit=1)
        
        default_folder = purchase_folder.id if purchase_folder else self.equipment_folder_id.id
        
        return {
            'name': _('Upload Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.document.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_folder_id': default_folder,
                'default_equipment_id': self.id,
            },
        }

    def action_view_folder(self):
        """Open the equipment folder in document manager"""
        self.ensure_one()
        
        if not self.equipment_folder_id:
            self._create_equipment_folder()
        
        return self.equipment_folder_id.action_view_folder_documents()

    def action_borrow(self):
        self.ensure_one()
        if self.holder_type != 'none':
            raise UserError(_('This item is assigned. Unassign it before borrowing.'))
        if self.state not in ['available', 'reserved']:
            raise UserError(_('Equipment must be available or reserved to borrow.'))
        return {
            'name': _('Borrow Equipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'equipment.borrow.wizard',
            'view_mode': 'form',
            'context': {
                'default_equipment_id': self.id,
                'default_from_location_id': self.location_id.id,
                'default_borrower_id': self.env.user.id,
            },
            'target': 'new',
        }

    def action_return(self):
        self.ensure_one()
        if self.state != 'borrowed':
            raise UserError(_('Only borrowed equipment can be returned.'))
        active_loan = self.active_loan_id
        if active_loan:
            return active_loan.action_return()
        raise UserError(_('No active loan found.'))

    def action_open_assign_wizard(self):
        self.ensure_one()
        if self.state == 'borrowed':
            raise UserError(_('Return this item before assigning it.'))
        if self.state in ['maintenance', 'retired', 'lost']:
            raise UserError(_('Cannot assign items in this state.'))
        return {
            'name': _('Assign Equipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'equipment.assign.wizard',
            'view_mode': 'form',
            'context': {
                'default_equipment_id': self.id,
                'default_holder_type': 'employee',
                'default_assigned_date': fields.Date.today(),
            },
            'target': 'new',
        }

    def action_open_unassign_wizard(self):
        self.ensure_one()
        if self.holder_type == 'none':
            raise UserError(_('This item is not assigned.'))
        if self.state == 'borrowed':
            raise UserError(_('Return this item before unassigning it.'))
        return {
            'name': _('Unassign Equipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'equipment.unassign.wizard',
            'view_mode': 'form',
            'context': {
                'default_equipment_id': self.id,
            },
            'target': 'new',
        }

    def action_move_to_store(self):
        ms = self.env.ref('equipment_management.location_main_store', raise_if_not_found=False)
        if not ms:
            raise UserError(_('Main Store location is missing.'))
        for rec in self:
            if rec.state == 'borrowed':
                raise UserError(_('Return the item before moving it to store.'))
            rec.write({
                'holder_type': 'none',
                'employee_id': False,
                'department_id': False,
                'custodian_partner_id': False,
                'assigned_date': False,
                'location_id': ms.id,
                'state': 'available' if rec.state not in ['maintenance', 'retired', 'lost', 'reserved'] else rec.state,
            })
        return True

    def action_schedule_maintenance(self):
        self.ensure_one()
        view = self.env.ref('equipment_management.view_equipment_maintenance_quick_form', raise_if_not_found=False)

        if not view:
            fallback = self.env['ir.ui.view'].search(
                [('model', '=', 'equipment.maintenance'), ('type', '=', 'form')],
                limit=1
            )
            view_id = fallback.id or False
        else:
            view_id = view.id

        ctx = {
            'default_equipment_id': self.id,
            'default_maintenance_type': 'preventive',
        }
        return {
            'name': _('Schedule Maintenance'),
            'type': 'ir.actions.act_window',
            'res_model': 'equipment.maintenance',
            'view_mode': 'form',
            **({'view_id': view_id} if view_id else {}),
            'context': ctx,
            'target': 'new',
        }

    def action_view_loans(self):
        self.ensure_one()
        return {
            'name': _('Loans for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'equipment.loan',
            'view_mode': 'tree,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'default_equipment_id': self.id},
        }

    def action_view_attachments(self):
        """Legacy - redirect to documents"""
        return self.action_view_documents()

    def action_print_barcode_label(self):
        self.ensure_one()
        return self.env.ref('equipment_management.action_report_equipment_barcode_label').report_action(self)

    def action_scan_equipment(self):
        return {
            'name': _('Scan Equipment'),
            'type': 'ir.actions.client',
            'tag': 'equipment_barcode_scanner',
            'target': 'fullscreen',
        }

    # Utility Methods
    def mark_as_lost(self):
        for item in self:
            item.write({
                'state': 'lost',
                'custodian_id': False,
            })
            item.message_post(
                body=_('Equipment marked as lost/missing.'),
                subject=_('Equipment Lost')
            )

    def mark_as_found(self):
        for item in self:
            if item.state == 'lost':
                item.write({'state': 'available'})
                item.message_post(
                    body=_('Equipment has been found and is now available.'),
                    subject=_('Equipment Found')
                )

    def retire_equipment(self):
        for item in self:
            if item.state == 'borrowed':
                raise UserError(_('Cannot retire borrowed equipment.'))
            item.write({
                'state': 'retired',
                'custodian_id': False,
            })
            item.message_post(
                body=_('Equipment has been retired.'),
                subject=_('Equipment Retired')
            )