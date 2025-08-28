# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class AssetReport(models.AbstractModel):
    _name = 'report.assets_management.report_asset'
    _description = 'Asset Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['asset.asset'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'asset.asset',
            'docs': docs,
        }


class AssetDepreciationReport(models.AbstractModel):
    _name = 'report.assets_management.report_asset_depreciation'
    _description = 'Asset Depreciation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['asset.asset'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'asset.asset',
            'docs': docs,
        }


class AssetListReport(models.AbstractModel):
    _name = 'report.assets_management.report_asset_list'
    _description = 'Asset List Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if data and data.get('form'):
            # Custom filters from wizard if implemented
            domain = []
            if data['form'].get('category_ids'):
                domain.append(('category_id', 'in', data['form']['category_ids']))
            if data['form'].get('state'):
                domain.append(('state', '=', data['form']['state']))
            docs = self.env['asset.asset'].search(domain)
        else:
            docs = self.env['asset.asset'].browse(docids) if docids else self.env['asset.asset'].search([])
        
        return {
            'doc_ids': docs.ids,
            'doc_model': 'asset.asset',
            'docs': docs,
        }


class AssetAnalysisReport(models.Model):
    _name = 'asset.analysis.report'
    _description = 'Asset Analysis Report'
    _auto = False
    _rec_name = 'asset_name'

    asset_id = fields.Many2one('asset.asset', string='Asset', readonly=True)
    asset_name = fields.Char(string='Asset Name', readonly=True)
    asset_code = fields.Char(string='Asset Code', readonly=True)
    category_id = fields.Many2one('asset.category', string='Category', readonly=True)
    category_name = fields.Char(string='Category Name', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('in_use', 'In Use'),
        ('in_maintenance', 'In Maintenance'),
        ('in_repair', 'In Repair'),
        ('disposed', 'Disposed'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('sold', 'Sold')
    ], string='Status', readonly=True)
    
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    custodian_id = fields.Many2one('hr.employee', string='Custodian', readonly=True)
    
    purchase_date = fields.Date(string='Purchase Date', readonly=True)
    purchase_value = fields.Monetary(string='Purchase Value', readonly=True)
    current_value = fields.Monetary(string='Current Value', readonly=True)
    accumulated_depreciation = fields.Monetary(string='Accumulated Depreciation', readonly=True)
    
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    
    maintenance_count = fields.Integer(string='Maintenance Count', readonly=True)
    repair_count = fields.Integer(string='Repair Count', readonly=True)
    total_maintenance_cost = fields.Monetary(string='Total Maintenance Cost', readonly=True)
    total_repair_cost = fields.Monetary(string='Total Repair Cost', readonly=True)

    def init(self):
        query = """
            CREATE OR REPLACE VIEW asset_analysis_report AS (
                SELECT 
                    row_number() OVER () AS id,
                    a.id as asset_id,
                    a.name as asset_name,
                    a.asset_code,
                    a.category_id,
                    c.name as category_name,
                    a.state,
                    a.department_id,
                    a.custodian_id,
                    a.purchase_date,
                    a.purchase_value,
                    a.current_value,
                    a.accumulated_depreciation,
                    a.currency_id,
                    a.company_id,
                    COALESCE(m.maintenance_count, 0) as maintenance_count,
                    COALESCE(r.repair_count, 0) as repair_count,
                    COALESCE(m.total_maintenance_cost, 0) as total_maintenance_cost,
                    COALESCE(r.total_repair_cost, 0) as total_repair_cost
                FROM 
                    asset_asset a
                LEFT JOIN 
                    asset_category c ON a.category_id = c.id
                LEFT JOIN (
                    SELECT 
                        asset_id,
                        COUNT(*) as maintenance_count,
                        SUM(COALESCE(cost, 0)) as total_maintenance_cost
                    FROM asset_maintenance 
                    GROUP BY asset_id
                ) m ON a.id = m.asset_id
                LEFT JOIN (
                    SELECT 
                        asset_id,
                        COUNT(*) as repair_count,
                        SUM(COALESCE(cost, 0)) as total_repair_cost
                    FROM asset_repair 
                    GROUP BY asset_id
                ) r ON a.id = r.asset_id
                WHERE a.active = true
            )
        """
        self.env.cr.execute(query)