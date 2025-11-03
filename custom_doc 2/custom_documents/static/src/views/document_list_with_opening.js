/** @odoo-module **/
// static/src/views/document_list_with_opening.js

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Custom List Controller for Documents
 * - Enables row click to open document form
 * - Keeps upload/folder creation buttons
 */
class DocumentListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    /**
     * Re-enable opening documents on row click
     * Shows the rich form view with PDF preview, chatter, etc.
     */
    async openRecord(record) {
        return this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'custom.document',
            res_id: record.resId,
            views: [[false, 'form']],
            target: 'current',
            context: this.props.context,
        });
    }

    /**
     * Helper to get current folder ID from context/domain
     */
    _getCurrentFolderId() {
        // Try context first
        if (this.props.context?.default_folder_id) {
            return this.props.context.default_folder_id;
        }
        
        // Try domain
        const found = (this.props.domain || []).find(
            (d) => Array.isArray(d) && 
                   d[0] === "folder_id" && 
                   (d[1] === "=" || d[1] === "child_of")
        );
        return found ? found[2] : false;
    }

    /**
     * Upload File button action
     */
    async onUploadFile() {
        const folderId = this._getCurrentFolderId();
        
        await this.action.doAction("custom_documents.action_custom_document_upload_file", {
            additionalContext: {
                default_document_type: "file",
                default_folder_id: folderId || false,
            },
        });
    }

    /**
     * Add URL button action
     */
    async onAddUrl() {
        const folderId = this._getCurrentFolderId();
        
        await this.action.doAction("custom_documents.action_custom_document_upload_url", {
            additionalContext: {
                default_document_type: "url",
                default_folder_id: folderId || false,
            },
        });
    }

    /**
     * Create Folder button action
     */
    async onCreateFolder() {
        const folderId = this._getCurrentFolderId();
        
        await this.action.doAction("custom_documents.action_custom_document_folder_wizard", {
            additionalContext: {
                default_parent_id: folderId || false,
            },
        });
    }
}

/**
 * Register the custom document list view
 */
export const customDocumentListView = {
    ...listView,
    Controller: DocumentListController,
    buttonTemplate: "custom_documents.CustomDocumentListButtons",
};

registry.category("views").add("custom_document_list", customDocumentListView);

console.log("✓ Document list view registered with opening enabled");