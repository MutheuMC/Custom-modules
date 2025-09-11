from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
import base64

class DocumentsController(http.Controller):
    
    @http.route('/documents/share/<string:access_token>', type='http', auth='public', website=True)
    def share_portal(self, access_token):
        """Display shared documents portal"""
        share = request.env['documents.share'].sudo().search([
            ('access_token', '=', access_token),
            ('state', '=', 'live')
        ], limit=1)
        
        if not share:
            return request.render('custom_documents.share_invalid')
        
        if share.share_type == 'ids':
            documents = share.document_ids
        else:
            domain = [('folder_id', '=', share.folder_id.id)]
            if share.include_sub_folders:
                domain = [('folder_id', 'child_of', share.folder_id.id)]
            documents = request.env['documents.document'].sudo().search(domain)
        
        return request.render('custom_documents.share_portal', {
            'share': share,
            'documents': documents,
        })
    
    @http.route('/documents/download/<int:document_id>/<string:access_token>', 
                type='http', auth='public')
    def download_shared_document(self, document_id, access_token):
        """Download a shared document"""
        share = request.env['documents.share'].sudo().search([
            ('access_token', '=', access_token),
            ('state', '=', 'live')
        ], limit=1)
        
        if not share:
            return request.not_found()
        
        document = request.env['documents.document'].sudo().browse(document_id)
        
        if share.share_type == 'ids' and document not in share.document_ids:
            return request.not_found()
        elif share.share_type == 'folder':
            if share.include_sub_folders:
                if document.folder_id not in share.folder_id.child_ids:
                    return request.not_found()
            elif document.folder_id != share.folder_id:
                return request.not_found()
        
        share.increment_download()
        
        return request.make_response(
            base64.b64decode(document.datas),
            headers=[
                ('Content-Type', document.mimetype or 'application/octet-stream'),
                ('Content-Disposition', f'attachment; filename={document.name}')
            ]
        )