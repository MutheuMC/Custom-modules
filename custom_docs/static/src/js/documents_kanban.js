odoo.define('custom_documents.DocumentsKanban', function (require) {
    'use strict';

    const KanbanController = require('web.KanbanController');
    const KanbanView = require('web.KanbanView');
    const viewRegistry = require('web.view_registry');

    const DocumentsKanbanController = KanbanController.extend({
        buttons_template: 'DocumentsKanbanView.buttons',
        
        events: _.extend({}, KanbanController.prototype.events, {
            'click .o_documents_upload': '_onUpload',
            'click .o_documents_request': '_onRequest',
            'click .o_documents_url': '_onAddUrl',
        }),

        _onUpload: function () {
            const self = this;
            const $fileInput = $('<input type="file" multiple="multiple"/>');
            $fileInput.on('change', function (e) {
                const files = e.target.files;
                self._uploadFiles(files);
            });
            $fileInput.click();
        },

        _uploadFiles: function (files) {
            const self = this;
            const context = this.model.get(this.handle).context;
            
            _.each(files, function (file) {
                const reader = new FileReader();
                reader.onload = function (upload) {
                    const data = upload.target.result;
                    const base64Data = data.split(',')[1];
                    
                    self._rpc({
                        model: 'documents.document',
                        method: 'create',
                        args: [{
                            name: file.name,
                            datas: base64Data,
                            folder_id: context.default_folder_id || false,
                            mimetype: file.type,
                        }],
                    }).then(function () {
                        self.reload();
                    });
                };
                reader.readAsDataURL(file);
            });
        },

        _onRequest: function () {
            const context = this.model.get(this.handle).context;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'documents.request.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_folder_id: context.default_folder_id || false,
                },
            });
        },

        _onAddUrl: function () {
            const self = this;
            const context = this.model.get(this.handle).context;
            
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'documents.document',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_type: 'url',
                    default_folder_id: context.default_folder_id || false,
                },
            });
        },
    });

    const DocumentsKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: DocumentsKanbanController,
        }),
    });

    viewRegistry.add('documents_kanban', DocumentsKanbanView);

    return DocumentsKanbanView;
});