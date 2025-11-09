from . import models

def post_init_hook(env):
    """Initialize folder structure after module installation"""
    folder_model = env['custom.document.folder']
    
    # Create virtual folders ONCE for the entire instance
    if not folder_model.sudo().search([('is_virtual', '=', True)], limit=1):
        folder_model.sudo()._ensure_virtual_folders()
    
    # Now create company-specific structures
    # Get the user who is installing (typically admin)
    user = env.user
    
    # Get all active companies (not just the ones the installing user has access to)
    # This ensures all companies get the structure
    companies = env['res.company'].sudo().search([])
    
    for company in companies:
        folder_model_sudo = folder_model.sudo().with_company(company)
        
        # Create Company root folder
        folder_model_sudo._get_company_root(company)
        
        # Create default company folders  
        folder_model_sudo._ensure_default_company_children(company)
        
        # Create employee folders if hr module is installed
        # FIXED: Check if the model exists, not if module is in env
        if 'hr.employee' in env.registry:
            folder_model_sudo._ensure_employees_root(company)
            # Only create folders for employees in this company
            employees = env['hr.employee'].sudo().search([('company_id', '=', company.id)])
            for emp in employees:
                folder_model_sudo._ensure_employee_folder(emp)