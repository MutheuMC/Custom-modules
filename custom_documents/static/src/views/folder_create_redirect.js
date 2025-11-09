/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

// ============================================
// FOLDER LIST CONTROLLER - Use Standard New Button
// ============================================
class FolderListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
    }
    
    /**
     * Override createRecord to open wizard instead of form
     * This is triggered by the standard "New" button
     */
    async createRecord() {
        const parentId = this._getCurrentFolderId();
        
        await this.action.doAction("custom_documents.action_custom_document_folder_wizard", {
            additionalContext: {
                default_parent_id: parentId || false,
            },
        });
    }

    /**
     * Get current folder ID from context or domain
     */
    _getCurrentFolderId() {
        // Try context first
        if (this.props.context?.default_parent_id) {
            return this.props.context.default_parent_id;
        }
        
        // Try searchpanel selection
        if (this.props.context?.searchpanel_default_parent_id) {
            return this.props.context.searchpanel_default_parent_id;
        }
        
        // Try domain
        const found = (this.props.domain || []).find(
            (d) => Array.isArray(d) && 
                   d[0] === "parent_id" && 
                   (d[1] === "=" || d[1] === "child_of")
        );
        return found ? found[2] : false;
    }

    /**
     * Override to handle folder clicks - show subfolders
     */
    async openRecord(record) {
        // Get the folder ID
        const folderId = record.resId;
        
        // Open a new view showing subfolders of this folder
        return this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Subfolders'),
            res_model: 'custom.document.folder',
            views: [[false, 'list'], [false, 'form']],
            domain: [['parent_id', '=', folderId]],
            context: {
                ...this.props.context,
                default_parent_id: folderId,
            },
            target: 'current',
        });
    }
}

// ============================================
// FOLDER FORM CONTROLLER
// ============================================
class FolderFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
    }
    
    /**
     * Override create to use wizard
     */
    async createRecord() {
        await this.action.doAction("custom_documents.action_custom_document_folder_wizard", {
            additionalContext: {
                active_model: "custom.document.folder",
                active_id: this.props.resId || false,
            },
        });
    }
}

// ============================================
// REGISTER VIEWS - NO CUSTOM BUTTON TEMPLATE
// ============================================
const folderListView = { 
    ...listView, 
    Controller: FolderListController,
    // REMOVED: buttonTemplate - Use default Odoo buttons
};

const folderFormView = { 
    ...formView, 
    Controller: FolderFormController 
};

registry.category("views").add("custom_folder_list", folderListView);
registry.category("views").add("custom_folder_form", folderFormView);

console.log("✓ Custom folder views registered with standard New button");