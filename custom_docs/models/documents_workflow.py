from datetime import timedelta
from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval

class DocumentsWorkflowRule(models.Model):
    _name = 'documents.workflow.rule'
    _description = 'Documents Workflow Rule'
    _order = 'sequence, id'
    
    name = fields.Char(string='Action Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True, string='Active')
    
    # Conditions
    folder_id = fields.Many2one('documents.folder', string='Related Folder',
                                required=True, ondelete='cascade')
    condition_type = fields.Selection([
        ('no_condition', 'No Condition'),
        ('tag', 'Tags'),
        ('domain', 'Domain')
    ], string='Condition Type', default='no_condition', required=True)
    
    required_tag_ids = fields.Many2many('documents.tag', 'documents_workflow_rule_tag_rel',
                                        'rule_id', 'tag_id', string='Required Tags',
                                        help='Document must have all these tags')
    excluded_tag_ids = fields.Many2many('documents.tag', 'documents_workflow_rule_exclude_tag_rel',
                                        'rule_id', 'tag_id', string='Excluded Tags',
                                        help='Document must not have any of these tags')
    domain = fields.Text(string='Domain', default='[]',
                         help='Domain to filter documents')
    
    # Actions
    create_model = fields.Selection(selection='_get_models', string='Create')
    
    # Tag actions
    remove_tag_ids = fields.Many2many('documents.tag', 'documents_rule_remove_tag_rel',
                                      'rule_id', 'tag_id', string='Remove Tags')
    add_tag_ids = fields.Many2many('documents.tag', 'documents_rule_add_tag_rel',
                                   'rule_id', 'tag_id', string='Add Tags')
    
    # Move action
    move_folder_id = fields.Many2one('documents.folder', string='Move to Folder')
    
    # Partner action
    set_partner_id = fields.Many2one('res.partner', string='Set Contact')
    
    # Owner action
    set_owner_id = fields.Many2one('res.users', string='Set Owner')
    
    # Activity action
    create_activity = fields.Boolean(string='Create Activity')
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    activity_summary = fields.Char(string='Activity Summary')
    activity_date_deadline_range = fields.Integer(string='Due Date In (days)')
    activity_user_id = fields.Many2one('res.users', string='Activity Assigned to')
    
    @api.model
    def _get_models(self):
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]
    
    def apply_actions(self, documents):
        """Apply workflow actions to documents"""
        for rule in self:
            if not rule._check_condition(documents):
                continue
                
            vals = {}
            
            # Tag actions
            if rule.add_tag_ids:
                vals['tag_ids'] = [(4, tag.id, 0) for tag in rule.add_tag_ids]
            if rule.remove_tag_ids:
                vals['tag_ids'] = vals.get('tag_ids', []) + [(3, tag.id, 0) for tag in rule.remove_tag_ids]
            
            # Move action
            if rule.move_folder_id:
                vals['folder_id'] = rule.move_folder_id.id
            
            # Partner action
            if rule.set_partner_id:
                vals['partner_id'] = rule.set_partner_id.id
            
            # Owner action
            if rule.set_owner_id:
                vals['owner_id'] = rule.set_owner_id.id
            
            if vals:
                documents.write(vals)
            
            # Activity action
            if rule.create_activity and rule.activity_type_id:
                for document in documents:
                    self.env['mail.activity'].create({
                        'res_model': 'documents.document',
                        'res_id': document.id,
                        'activity_type_id': rule.activity_type_id.id,
                        'summary': rule.activity_summary or rule.name,
                        'date_deadline': fields.Date.today() + timedelta(days=rule.activity_date_deadline_range or 0),
                        'user_id': (rule.activity_user_id or document.owner_id or self.env.user).id,
                    })
            
            # Create model action
            if rule.create_model:
                rule._create_record(documents)
    
    def _check_condition(self, documents):
        """Check if documents meet the rule conditions"""
        self.ensure_one()
        
        if self.condition_type == 'no_condition':
            return True
        
        elif self.condition_type == 'tag':
            for document in documents:
                if self.required_tag_ids and not all(tag in document.tag_ids for tag in self.required_tag_ids):
                    return False
                if self.excluded_tag_ids and any(tag in document.tag_ids for tag in self.excluded_tag_ids):
                    return False
            return True
        
        elif self.condition_type == 'domain':
            domain = safe_eval(self.domain or '[]')
            matching = documents.filtered_domain(domain)
            return len(matching) == len(documents)
        
        return False
    
    def _create_record(self, documents):
        """Create records based on the workflow rule"""
        self.ensure_one()
        if not self.create_model:
            return
        
        Model = self.env[self.create_model]
        for document in documents:
            vals = {
                'name': document.name,
            }
            
            # Add document as attachment if the model has an attachment field
            if 'attachment_ids' in Model._fields:
                attachment = self.env['ir.attachment'].create({
                    'name': document.name,
                    'datas': document.datas,
                    'res_model': self.create_model,
                    'res_id': 0,
                })
                vals['attachment_ids'] = [(4, attachment.id)]
            
            Model.create(vals)
