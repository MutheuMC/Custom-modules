import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { Component } from "@odoo/owl";

export class DocumentsKanbanController extends KanbanController {
    static template = "custom_docs.DocumentsKanbanController";
    static components = {
        ...KanbanController.components,
        Dropdown,
        DropdownItem,
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    /**
     * Handle file upload
     */
    async onUploadDocuments(ev) {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = '*/*';
        
        input.onchange = async (event) => {
            const files = event.target.files;
            if (files.length === 0) return;
            
            const context = this.props.context;
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
                    await this.orm.create("documents.document", [{
                        name: file.name,
                        datas: base64,
                        folder_id: folderId,
                        mimetype: file.type || 'application/octet-stream',
                        type: 'binary',
                    }]);
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
    async onAddUrl(ev) {
        const context = this.props.context;
        
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
    async onRequestDocument(ev) {
        const context = this.props.context;
        
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
     * Handle new folder creation
     */
    async onNewFolder(ev) {
        const context = this.props.context;
        
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "documents.folder",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_parent_folder_id: context.default_folder_id || false,
            },
        });
    }

    /**
     * Create new spreadsheet
     */
    async onNewSpreadsheet(ev) {
        const context = this.props.context;
        
        // For now, create an empty document - you can integrate with Odoo spreadsheet module later
        this.notification.add(
            _t("Spreadsheet creation will be available soon"),
            { type: "info" }
        );
    }

    /**
     * Handle bulk download
     */
    async onDownloadDocuments() {
        const selection = [...this.model.root.selection];
        
        if (selection.length === 0) {
            this.notification.add(
                _t("Please select documents to download"),
                { type: "warning" }
            );
            return;
        }
        
        for (const record of selection) {
            if (record.data.type === 'binary') {
                window.open(`/web/content/documents.document/${record.resId}/datas?download=true`);
            }
        }
    }

    /**
     * Handle bulk share
     */
    async onShareDocuments() {
        const selection = [...this.model.root.selection];
        
        if (selection.length === 0) {
            this.notification.add(
                _t("Please select documents to share"),
                { type: "warning" }
            );
            return;
        }
        
        const documentIds = selection.map(r => r.resId);
        const context = this.props.context;
        
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