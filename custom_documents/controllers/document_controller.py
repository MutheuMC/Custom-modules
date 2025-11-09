from odoo import http
from odoo.http import request, content_disposition
import base64

class DocumentPDFController(http.Controller):
    
    @http.route('/document/pdf/view/<int:document_id>', type='http', auth='user')
    def view_pdf(self, document_id, **kwargs):
        document = request.env['custom.document'].browse(document_id)
        if document.exists() and document.document_type == 'file' and document.mimetype == 'application/pdf':
            pdf_data = base64.b64decode(document.file)
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_data)),
            ]
            return request.make_response(pdf_data, headers)
        return request.not_found()