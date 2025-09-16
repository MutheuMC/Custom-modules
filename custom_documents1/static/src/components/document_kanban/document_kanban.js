
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { DocumentDropdown } from "../document_dropdown/document_dropdown";
import { useService } from "@web/core/utils/hooks";

export class CustomDocumentKanbanController extends KanbanController {
    static template = "custom_documents.KanbanController";
    static components = {
        ...KanbanController.components,
        DocumentDropdown,
    };

    setup() {
        super.setup();
        this.currentFolderId = this.props.context.default_folder_id || false;
    }
}

export const customDocumentKanbanView = {
    ...kanbanView,
    Controller: CustomDocumentKanbanController,
};

registry.category("views").add("custom_document_kanban", customDocumentKanbanView);