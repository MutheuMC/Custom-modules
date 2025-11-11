from . import models

def post_init_hook(env):
    """Initialize folder structure after module installation"""
    folder_model = env['custom.document.folder']
    
    # Get all active companies
    companies = env['res.company'].sudo().search([])
    
    for company in companies:
        folder_model_sudo = folder_model.sudo().with_company(company)
        
        # Create Company root folder
        folder_model_sudo._get_company_root(company)
        
        # Create default company folders  
        folder_model_sudo._ensure_default_company_children(company)
        
        # Create employee folders if hr module is installed
        if 'hr.employee' in env.registry:
            folder_model_sudo._ensure_employees_root(company)
            employees = env['hr.employee'].sudo().search([('company_id', '=', company.id)])
            for emp in employees:
                folder_model_sudo._ensure_employee_folder(emp)