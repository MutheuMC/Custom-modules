# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, content_disposition
import base64

class DocumentPublicShareController(http.Controller):

    @http.route('/documents/s/<string:token>', type='http', auth='public')
    def public_share(self, token, download=False, **kw):
        Doc = request.env['custom.document'].sudo()
        doc = Doc.search(['|', ('share_token_view', '=', token), ('share_token_edit', '=', token)], limit=1)
        if not doc or doc.document_type != 'file' or not doc.file:
            return request.not_found()

        # enforce share mode
        if token == doc.share_token_view and doc.share_access not in ('link_view', 'link_edit'):
            return request.not_found()
        if token == doc.share_token_edit and doc.share_access != 'link_edit':
            return request.not_found()

        data = base64.b64decode(doc.with_context(bin_size=False).file)
        headers = [('Content-Type', doc.mimetype or 'application/octet-stream')]
        if str(download).lower() in ('1', 'true', 'yes'):
            headers.append(('Content-Disposition', content_disposition(doc.file_name or doc.name)))
        return request.make_response(data, headers)
