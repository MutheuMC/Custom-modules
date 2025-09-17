/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation"; // Import translation function

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";

class CustomDocumentListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
        this.currentFolderId = this.props.context?.default_folder_id || false;
        // Use imported _t function instead of this.env._t
        this.props.createText = _t("Upload");
    }
    async createRecord() {
        await this.action.doAction("custom_documents.action_custom_document_upload_wizard", {
            additionalContext: { default_folder_id: this.currentFolderId },
        });
    }
    async onClickCreate() {
        return this.createRecord();
    }
}

class CustomDocumentKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.action = useService("action");
        this.currentFolderId = this.props.context?.default_folder_id || false;
        // Use imported _t function instead of this.env._t
        this.props.createText = _t("Upload");
    }
    async createRecord() {
        await this.action.doAction("custom_documents.action_custom_document_upload_wizard", {
            additionalContext: { default_folder_id: this.currentFolderId },
        });
    }
    async onClickCreate() {
        return this.createRecord();
    }
}

const customDocumentListView = { ...listView, Controller: CustomDocumentListController };
const customDocumentKanbanView = { ...kanbanView, Controller: CustomDocumentKanbanController };

registry.category("views").add("custom_document_list", customDocumentListView);
registry.category("views").add("custom_document_kanban", customDocumentKanbanView);