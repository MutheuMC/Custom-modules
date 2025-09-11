/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DocumentsKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    /**
     * Handle file upload
     */
    async onUploadDocuments() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = '*/*';
        
        input.onchange = async (event) => {
            const files = event.target.files;
            if (files.length === 0) return;
            
            const context = this.model.config.context;
            const folderId = context.default_folder_id || false;
            
            try {
                for (const file of files) {
                    await this._uploadFile(file, folderId);
                }
                
                this.notification.add(
                    _t("Documents uploaded successfully"),
                    { type: "success" }
                );
                
                // Reload the view to show new documents
                await this.model.load();
                this.render(true);
                
            } catch (error) {
                this.notification.add(
                    _t("Error uploading documents"),
                    { type: "danger" }
                );
                console.error("Upload error:", error);
            }
        };
        
        input.click();
    }

    /**
     * Upload a single file
     */
    async _uploadFile(file, folderId) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                const base64 = e.target.result.split(',')[1];
                
                try {
                    await this.rpc("/web/dataset/call_kw/documents.document/create", {
                        model: "documents.document",
                        method: "create",
                        args: [{
                            name: file.name,
                            datas: base64,
                            folder_id: folderId,
                            mimetype: file.type || 'application/octet-stream',
                            type: 'binary',
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

    /**
     * Handle URL document creation
     */
    async onAddUrl() {
        const context = this.model.config.context;
        
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "documents.document",
            views: [[false, "form"]],
            target: "new",
            context: {
                ...context,
                default_type: 'url',
                default_folder_id: context.default_folder_id || false,
            },
        });
    }

    /**
     * Handle document request
     */
    async onRequestDocument() {
        const context = this.model.config.context;
        
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "documents.request.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_folder_id: context.default_folder_id || false,
            },
        });
    }

    /**
     * Handle bulk download
     */
    async onDownloadDocuments() {
        const selectedRecords = this.model.root.selection;
        
        if (selectedRecords.length === 0) {
            this.notification.add(
                _t("Please select documents to download"),
                { type: "warning" }
            );
            return;
        }
        
        for (const record of selectedRecords) {
            if (record.data.type === 'binary') {
                window.open(`/web/content/documents.document/${record.resId}/datas?download=true`);
            }
        }
    }

    /**
     * Handle bulk share
     */
    async onShareDocuments() {
        const selectedRecords = this.model.root.selection;
        
        if (selectedRecords.length === 0) {
            this.notification.add(
                _t("Please select documents to share"),
                { type: "warning" }
            );
            return;
        }
        
        const documentIds = selectedRecords.map(r => r.resId);
        const context = this.model.config.context;
        
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "documents.share",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_document_ids: [[6, 0, documentIds]],
                default_folder_id: context.default_folder_id || false,
                default_share_type: 'ids',
            },
        });
    }
}

DocumentsKanbanController.template = "custom_docs.DocumentsKanbanController";