
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { DocumentDropdown } from "../components/document_dropdown/document_dropdown";

export class CustomDocumentListController extends ListController {
    static template = "custom_documents.ListController";
    static components = {
        ...ListController.components,
        DocumentDropdown,
    };

    setup() {
        super.setup();
        this.currentFolderId = this.props.context?.default_folder_id || false;
    }
}

export const customDocumentListView = {
    ...listView,
    Controller: CustomDocumentListController,
};

// Register the custom list view for the document model
registry.category("views").add("custom_document_list", customDocumentListView);