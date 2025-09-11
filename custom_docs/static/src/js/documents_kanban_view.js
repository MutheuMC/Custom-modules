import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { DocumentsKanbanController } from "./documents_kanban_controller";

// Create the custom kanban view with our controller
export const documentsKanbanView = {
    ...kanbanView,
    Controller: DocumentsKanbanController,
};

// Register the view
registry.category("views").add("documents_kanban", documentsKanbanView);