import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { DocumentsKanbanController } from "./documents_kanban_controller";
import { DocumentsKanbanRenderer } from "./documents_kanban_renderer";

export const documentsKanbanView = {
    ...kanbanView,
    Controller: DocumentsKanbanController,
    Renderer: DocumentsKanbanRenderer,
    buttonTemplate: "custom_docs.DocumentsKanbanController.Buttons",
};

// Register the custom view
registry.category("views").add("documents_kanban", documentsKanbanView);