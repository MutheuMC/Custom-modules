from odoo import api, fields, models, _

class DocumentsRequestWizard(models.TransientModel):
    _name = 'documents.request.wizard'
    _description = 'Request Document Wizard'
    
    name = fields.Char(string='Document Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Request From', required=True)
    folder_id = fields.Many2one('documents.folder', string='Folder', required=True)
    tag_ids = fields.Many2many('documents.tag', string='Tags')
    deadline = fields.Date(string='Deadline')
    message = fields.Text(string='Message')
    
    def action_request_document(self):
        self.ensure_one()
        
        # Create empty document (request)
        document = self.env['documents.document'].create({
            'name': self.name,
            'type': 'empty',
            'folder_id': self.folder_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'request_partner_id': self.partner_id.id,
            'request_date': fields.Date.today(),
            'request_deadline': self.deadline,
            'request_message': self.message,
        })
        
        # Create activity
        if self.deadline:
            self.env['mail.activity'].create({
                'res_model': 'documents.document',
                'res_id': document.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Upload requested document: %s') % self.name,
                'date_deadline': self.deadline,
                'user_id': self.env.user.id,
            })
        
        # Send email notification
        template = self.env.ref('custom_docs.email_template_document_request', raise_if_not_found=False)
        if template:
            template.send_mail(document.id, force_send=True)
        
        return {'type': 'ir.actions.act_window_close'}