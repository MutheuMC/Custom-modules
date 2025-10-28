# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, content_disposition
import base64
import html
import logging

_logger = logging.getLogger(__name__)

class DocumentShareController(http.Controller):
    """Public token-based sharing without website module."""

    @http.route('/documents/s/<string:token>', type='http', auth='public')
    def share_document(self, token, download=None, **kwargs):
        """Serve the file inline (PDF/images) or as download."""
        try:
            doc = self._find_document_by_token(token)
            if not doc:
                return self._html_error(404, 'Document Not Found',
                                        'This share link is invalid or may have expired.')

            if not self._validate_token_access(doc, token):
                return self._html_error(403, 'Access Denied',
                                        'This share link is no longer active. Contact the document owner.')

            if doc.document_type != 'file' or not doc.file:
                return self._html_error(400, 'Invalid Document',
                                        'This document cannot be accessed via link.')

            self._log_access(doc, token)
            return self._serve_document(doc, force_download=bool(download))

        except Exception as e:
            _logger.exception("Share controller error")
            return self._html_error(500, 'Error', f'An unexpected error occurred: {html.escape(str(e))}')

    @http.route('/documents/s/<string:token>/download', type='http', auth='public')
    def share_download(self, token, **kwargs):
        """Force download."""
        return self.share_document(token, download='1', **kwargs)

    @http.route('/documents/check/<string:token>', type='json', auth='public')
    def check_token(self, token):
        """JSON validity check (useful for clients)."""
        doc = self._find_document_by_token(token)
        if not doc:
            return {'valid': False, 'message': 'Token not found'}
        if not self._validate_token_access(doc, token):
            return {'valid': False, 'message': 'Access denied'}
        return {
            'valid': True,
            'document_name': doc.name,
            'document_type': doc.document_type,
            'file_size': doc.file_size,
            'mimetype': doc.mimetype,
            'access_type': 'edit' if token == doc.share_token_edit else 'view',
        }

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _find_document_by_token(self, token):
        Doc = request.env['custom.document'].sudo()
        return Doc.search([
            '|',
            ('share_token_view', '=', token),
            ('share_token_edit', '=', token)
        ], limit=1)

    def _validate_token_access(self, doc, token):
        if not doc or not token:
            return False
        if token == doc.share_token_view:
            return doc.share_access in ('link_view', 'link_edit')
        if token == doc.share_token_edit:
            return doc.share_access == 'link_edit'
        return False

    def _serve_document(self, doc, force_download=False):
        file_data = base64.b64decode(doc.with_context(bin_size=False).file)
        filename = doc.file_name or doc.name or 'document'
        headers = [
            ('Content-Type', doc.mimetype or 'application/octet-stream'),
            ('Content-Length', str(len(file_data))),
            ('Cache-Control', 'public, max-age=3600'),
            ('X-Content-Type-Options', 'nosniff'),
        ]
        # Inline preview for common types; else download
        if force_download or not self._can_display_inline(doc.mimetype):
            headers.append(('Content-Disposition', content_disposition(filename)))
        else:
            headers.append(('Content-Disposition', f'inline; filename="{filename}"'))
        return request.make_response(file_data, headers)

    def _can_display_inline(self, mimetype):
        inline_types = {
            'application/pdf',
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
            'text/plain',
        }
        return mimetype in inline_types if mimetype else False

    def _log_access(self, doc, token):
        try:
            access_type = 'view' if token == doc.share_token_view else 'edit'
            doc.sudo().message_post(
                body=f'Document accessed via {access_type} link',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        except Exception as e:
            _logger.warning("Could not log access: %s", e)

    def _html_error(self, status, title, message):
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, 'Helvetica Neue', Arial, sans-serif;
            background:#f8f9fa; margin:0; padding:0; }}
    .wrap {{ min-height: 60vh; display:flex; align-items:center; justify-content:center; }}
    .box {{ max-width:560px; background:#fff; padding:28px; border-radius:10px;
           box-shadow:0 2px 8px rgba(0,0,0,.08); text-align:center; }}
    h1 {{ margin:0 0 10px; font-size:22px; color:#212529; }}
    p  {{ margin:0 0 16px; color:#6c757d; line-height:1.5; }}
    a.btn {{ display:inline-block; padding:10px 16px; border-radius:8px; text-decoration:none;
             background:#0d6efd; color:#fff; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="box">
      <h1>{html.escape(title)}</h1>
      <p>{html.escape(message)}</p>
      <p><a class="btn" href="/web">Go to Home</a></p>
    </div>
  </div>
</body>
</html>"""
        return request.make_response(html_body, [('Content-Type', 'text/html')], status=status)
