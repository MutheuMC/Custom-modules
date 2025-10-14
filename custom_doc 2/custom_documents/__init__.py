from . import models

def post_init_hook(env):
    """Initialize folder structure after module installation"""
    folder_model = env['custom.document.folder']
    
    # Create virtual folders ONCE for the entire instance
    if not folder_model.sudo().search([('is_virtual', '=', True)], limit=1):
        folder_model._ensure_virtual_folders()
    
    # Now create company-specific structures
    companies = env['res.company'].search([])
    for company in companies:
        folder_model = folder_model.with_company(company)
        
        # Create Company root folder
        folder_model._get_company_root(company)
        
        # Create default company folders  
        folder_model._ensure_default_company_children(company)
        
        # Create employee folders if hr.employee is installed
        if 'hr.employee' in env:
            folder_model._ensure_employees_root(company)
            employees = env['hr.employee'].search([('company_id', '=', company.id)])
            for emp in employees:
                folder_model._ensure_employee_folder(emp)