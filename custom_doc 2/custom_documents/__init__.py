from . import models

def post_init_hook(env):
    """Initialize folder structure after module installation"""
    # Initialize folder structure for all companies
    companies = env['res.company'].search([])
    folder_model = env['custom.document.folder']
    
    for company in companies:
        # Switch to company context
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