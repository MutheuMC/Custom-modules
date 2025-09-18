odoo.define('custom_documents.DocumentViewer', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var DocumentFormController = FormController.extend({
        /**
         * @override
         */
        _onButtonClicked: function (event) {
            if (event.data.attrs.name === 'action_view_file') {
                this._openPDFViewer();
            } else {
                this._super.apply(this, arguments);
            }
        },

        _openPDFViewer: function () {
            var record = this.model.get(this.handle);
            if (record.data.document_type === 'file' && record.data.mimetype === 'application/pdf') {
                // Open PDF in a dialog or new tab
                window.open(record.data.file_view_url, '_blank');
            }
        },
    });

    var DocumentFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: DocumentFormController,
        }),
    });

    viewRegistry.add('custom_document_form', DocumentFormView);
});