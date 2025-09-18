/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

// Folder List Controller
class FolderListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
    }
    
    get createText() {
        return _t("Create Folder");
    }
    
    async createRecord() {
        await this.action.doAction("custom_documents.action_custom_document_folder_wizard");
    }
}

// Folder Form Controller
class FolderFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
    }
    
    async createRecord() {
        await this.action.doAction("custom_documents.action_custom_document_folder_wizard", {
            additionalContext: {
                active_model: "custom.document.folder",
                active_id: this.props.resId || false,
            },
        });
    }
}

// Register the folder views
const folderListView = { 
    ...listView, 
    Controller: FolderListController 
};

const folderFormView = { 
    ...formView, 
    Controller: FolderFormController 
};

registry.category("views").add("custom_folder_list", folderListView);
registry.category("views").add("custom_folder_form", folderFormView);