# -*- coding: utf-8 -*-
import base64
import zipfile
import io
import os
import mimetypes
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class FolderUploadWizard(models.TransientModel):
    _name = 'custom.document.folder.upload.wizard'
    _description = 'Upload Folder with Documents'

    name = fields.Char('Folder Name', help='Leave empty to use uploaded folder name')
    parent_folder_id = fields.Many2one('custom.document.folder', string='Upload To')
    
    # Upload options
    upload_type = fields.Selection([
        ('zip', 'Upload ZIP Archive'),
        ('multiple', 'Upload Multiple Files'),
    ], string='Upload Method', default='zip', required=True)
    
    # For ZIP upload
    zip_file = fields.Binary('ZIP File', help='Upload a ZIP file containing your folder structure')
    zip_filename = fields.Char('ZIP Filename')
    
    # For multiple file upload
    file_ids = fields.One2many('custom.document.folder.upload.file', 'wizard_id', string='Files')
    
    # Options
    create_subfolders = fields.Boolean(
        'Create Subfolders', 
        default=True,
        help='Create folder structure from ZIP (nested folders)'
    )
    skip_existing = fields.Boolean(
        'Skip Existing Files',
        default=False,
        help='Skip files that already exist instead of creating duplicates'
    )
    
    # Results
    folders_created = fields.Integer('Folders Created', readonly=True)
    files_uploaded = fields.Integer('Files Uploaded', readonly=True)
    files_skipped = fields.Integer('Files Skipped', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Set default parent folder from context"""
        res = super().default_get(fields_list)
        
        # Get folder from context
        folder_id = self.env.context.get('default_parent_folder_id')
        if not folder_id:
            folder_id = self.env.context.get('default_folder_id')
        if not folder_id and self.env.context.get('active_model') == 'custom.document.folder':
            folder_id = self.env.context.get('active_id')
        
        if folder_id:
            res['parent_folder_id'] = folder_id
            
        return res

    def _get_or_create_folder(self, folder_path, parent_folder=None):
        """Get or create a folder by path"""
        if not folder_path or folder_path == '.':
            return parent_folder
        
        # Split path into parts
        parts = folder_path.split('/')
        current_parent = parent_folder or self.parent_folder_id
        
        for part in parts:
            if not part or part == '.':
                continue
                
            # Search for existing folder
            folder = self.env['custom.document.folder'].search([
                ('name', '=', part),
                ('parent_id', '=', current_parent.id if current_parent else False),
            ], limit=1)
            
            if not folder:
                # Create new folder
                folder = self.env['custom.document.folder'].create({
                    'name': part,
                    'parent_id': current_parent.id if current_parent else False,
                    'user_id': self.env.user.id,
                    'company_id': self.env.company.id,
                })
                self.folders_created += 1
                _logger.info(f"Created folder: {part} (parent: {current_parent.name if current_parent else 'Root'})")
            
            current_parent = folder
        
        return current_parent

    def _check_file_exists(self, filename, folder):
        """Check if file already exists in folder"""
        return self.env['custom.document'].search([
            ('file_name', '=', filename),
            ('folder_id', '=', folder.id if folder else False),
        ], limit=1)

    def _create_document(self, filename, file_data, folder, subfolder_path=''):
        """Create a document from file data"""
        # Check if file exists
        if self.skip_existing and self._check_file_exists(filename, folder):
            self.files_skipped += 1
            _logger.info(f"Skipped existing file: {filename}")
            return None
        
        # Guess mimetype
        mimetype, _ = mimetypes.guess_type(filename)
        
        # Create document
        doc = self.env['custom.document'].create({
            'name': os.path.splitext(filename)[0],  # Remove extension
            'document_type': 'file',
            'file': base64.b64encode(file_data),
            'file_name': filename,
            'mimetype': mimetype or 'application/octet-stream',
            'folder_id': folder.id if folder else False,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
        })
        
        self.files_uploaded += 1
        _logger.info(f"Uploaded file: {filename} to folder: {folder.name if folder else 'Root'}")
        return doc

    def _process_zip_file(self):
        """Process ZIP file and extract documents"""
        if not self.zip_file:
            raise UserError(_('Please upload a ZIP file.'))
        
        try:
            # Decode ZIP file
            zip_data = base64.b64decode(self.zip_file)
            zip_buffer = io.BytesIO(zip_data)
            
            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                # Get all files in ZIP
                file_list = zip_ref.namelist()
                _logger.info(f"Processing ZIP with {len(file_list)} items")
                
                for file_path in file_list:
                    # Skip directories and hidden files
                    if file_path.endswith('/') or file_path.startswith('.') or '/.':
                        continue
                    
                    # Get file info
                    filename = os.path.basename(file_path)
                    folder_path = os.path.dirname(file_path)
                    
                    # Skip __MACOSX and other system folders
                    if '__MACOSX' in file_path or '.DS_Store' in file_path:
                        continue
                    
                    # Create folder structure if enabled
                    target_folder = self.parent_folder_id
                    if self.create_subfolders and folder_path:
                        target_folder = self._get_or_create_folder(folder_path, self.parent_folder_id)
                    
                    # Read file data
                    file_data = zip_ref.read(file_path)
                    
                    # Create document
                    self._create_document(filename, file_data, target_folder, folder_path)
                    
        except zipfile.BadZipFile:
            raise UserError(_('Invalid ZIP file. Please upload a valid ZIP archive.'))
        except Exception as e:
            _logger.error(f"Error processing ZIP file: {str(e)}")
            raise UserError(_('Error processing ZIP file: %s') % str(e))

    def _process_multiple_files(self):
        """Process multiple uploaded files"""
        if not self.file_ids:
            raise UserError(_('Please upload at least one file.'))
        
        for file_line in self.file_ids:
            if not file_line.file or not file_line.filename:
                continue
            
            # Decode file
            file_data = base64.b64decode(file_line.file)
            
            # Determine target folder
            target_folder = self.parent_folder_id
            if self.create_subfolders and file_line.folder_path:
                target_folder = self._get_or_create_folder(file_line.folder_path, self.parent_folder_id)
            
            # Create document
            self._create_document(file_line.filename, file_data, target_folder)

    def action_upload(self):
        """Process upload based on selected method"""
        self.ensure_one()
        
        # Reset counters
        self.write({
            'folders_created': 0,
            'files_uploaded': 0,
            'files_skipped': 0,
        })
        
        try:
            if self.upload_type == 'zip':
                self._process_zip_file()
            else:
                self._process_multiple_files()
            
            # Show success message
            message = _(
                'Upload completed!\n\n'
                '✓ Folders created: %s\n'
                '✓ Files uploaded: %s\n'
                '⊘ Files skipped: %s'
            ) % (self.folders_created, self.files_uploaded, self.files_skipped)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Upload Successful'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'custom.document',
                        'view_mode': 'list,form',
                        'domain': [('folder_id', '=', self.parent_folder_id.id if self.parent_folder_id else False)],
                        'context': {'default_folder_id': self.parent_folder_id.id if self.parent_folder_id else False},
                    }
                }
            }
            
        except Exception as e:
            raise UserError(_('Upload failed: %s') % str(e))


class FolderUploadFile(models.TransientModel):
    """For multiple file upload option"""
    _name = 'custom.document.folder.upload.file'
    _description = 'Upload File Line'
    
    wizard_id = fields.Many2one('custom.document.folder.upload.wizard', required=True, ondelete='cascade')
    file = fields.Binary('File', required=True, attachment=True)
    filename = fields.Char('Filename', required=True)
    folder_path = fields.Char('Folder Path', help='Optional: relative folder path (e.g., "Documents/Images")')