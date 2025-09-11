// custom_documents/static/src/js/documents_kanban_controller.js
/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useState, useRef } from "@odoo/owl";

export class DocumentsKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        this.fileInputRef = useRef("fileInput");
    }

    async onUploadClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.fileInputRef.el) {
            this.fileInputRef.el.click();
        }
    }

    async onFileInputChange(ev) {
        const files = ev.target.files;
        if (files.length > 0) {
            await this.uploadFiles(files);
            // Reset the input
            ev.target.value = '';
        }
    }

    async uploadFiles(files) {
        const context = this.props.context;
        const promises = [];

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            promises.push(this.uploadFile(file, context));
        }

        try {
            await Promise.all(promises);
            this.notification.add(_t("Files uploaded successfully"), {
                type: "success",
            });
            // Reload the view
            await this.model.load();
        } catch (error) {
            this.notification.add(_t("Error uploading files"), {
                type: "danger",
            });
            console.error("Upload error:", error);
        }
    }

    uploadFile(file, context) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (upload) => {
                try {
                    const data = upload.target.result;
                    const base64Data = data.split(',')[1];
                    
                    await this.rpc("/web/dataset/call_kw/documents.document/create", {
                        model: 'documents.document',
                        method: 'create',
                        args: [{
                            name: file.name,
                            datas: base64Data,
                            folder_id: context.default_folder_id || false,
                            mimetype: file.type,
                        }],
                        kwargs: {},
                    });
                    resolve();
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    async onRequestClick(ev) {
        ev.preventDefault();
        const context = this.props.context;
        
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'documents.request.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                ...context,
                default_folder_id: context.default_folder_id || false,
            },
        });
    }

    async onAddUrlClick(ev) {
        ev.preventDefault();
        const context = this.props.context;
        
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'documents.document',
            views: [[false, 'form']],
            target: 'new',
            context: {
                ...context,
                default_type: 'url',
                default_folder_id: context.default_folder_id || false,
            },
        });
    }

    async onAddSpreadsheetClick(ev) {
        ev.preventDefault();
        const context = this.props.context;
        
        try {
            // Create a new spreadsheet document
            const documentId = await this.rpc("/web/dataset/call_kw/documents.document/create", {
                model: 'documents.document',
                method: 'create',
                args: [{
                    name: _t('New Spreadsheet'),
                    type: 'binary',
                    folder_id: context.default_folder_id || false,
                    mimetype: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                }],
                kwargs: {},
            });

            // Open the document in form view
            await this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'documents.document',
                res_id: documentId,
                views: [[false, 'form']],
                target: 'current',
            });
        } catch (error) {
            this.notification.add(_t("Error creating spreadsheet"), {
                type: "danger",
            });
            console.error("Spreadsheet creation error:", error);
        }
    }

    async onAddFolderClick(ev) {
        ev.preventDefault();
        const context = this.props.context;
        
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'documents.folder',
            views: [[false, 'form']],
            target: 'new',
            context: {
                ...context,
                default_parent_folder_id: context.default_folder_id || false,
            },
        });
    }
}

DocumentsKanbanController.template = "custom_documents.DocumentsKanbanController";