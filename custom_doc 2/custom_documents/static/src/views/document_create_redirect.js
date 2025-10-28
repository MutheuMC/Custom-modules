/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { onMounted, onWillUnmount } from "@odoo/owl";

/* ---------------------------
 *  LIST: controller + buttons
 * --------------------------*/
class CustomDocumentListController extends ListController {
  setup() {
    super.setup();
    this.action = useService("action");

    // Intercept anchor clicks inside data rows to avoid navigation
    this._blockRowAnchors = (ev) => {
      const anchor = ev.target.closest(".o_list_view .o_data_row a");
      if (!anchor) return;
      // Allow the row selector/checkbox
      if (anchor.classList.contains("o_list_record_selector")) return;
      ev.preventDefault();
      ev.stopPropagation();
    };

    onMounted(() => {
      // Capture phase so we stop it before default handlers
      this.el?.addEventListener("click", this._blockRowAnchors, true);
      this.el?.addEventListener("dblclick", this._blockRowAnchors, true);
    });
    onWillUnmount(() => {
      this.el?.removeEventListener("click", this._blockRowAnchors, true);
      this.el?.removeEventListener("dblclick", this._blockRowAnchors, true);
    });
  }

  // Hard-block all programmatic opens (row click, Enter key, dblclick)
  async openRecord(/*record, options*/) {
    return; // no-op
  }

  // Helpers used by the dropdown buttons
  _getCurrentFolderId() {
    if (this.props.context?.default_folder_id) {
      return this.props.context.default_folder_id;
    }
    // Check domain for folder_id
    const found = (this.props.domain || []).find(
      (d) =>
        Array.isArray(d) &&
        d[0] === "folder_id" &&
        (d[1] === "=" || d[1] === "child_of")
    );
    return found ? found[2] : false;
  }

  async onUploadFile() {
    const folderId = this._getCurrentFolderId();
    console.log("📁 Upload file clicked, folder ID:", folderId);

    await this.action.doAction("custom_documents.action_custom_document_upload_file", {
      additionalContext: {
        default_document_type: "file",
        default_folder_id: folderId || false,
      },
    });
  }

  async onAddUrl() {
    const folderId = this._getCurrentFolderId();
    console.log("🔗 Add URL clicked, folder ID:", folderId);

    await this.action.doAction("custom_documents.action_custom_document_upload_url", {
      additionalContext: {
        default_document_type: "url",
        default_folder_id: folderId || false,
      },
    });
  }

  async onCreateFolder() {
    const folderId = this._getCurrentFolderId();
    console.log("📂 Create folder clicked, parent folder ID:", folderId);

    await this.action.doAction("custom_documents.action_custom_document_folder_wizard", {
      additionalContext: {
        default_parent_id: folderId || false,
      },
    });
  }

  // New: open the Tag wizard
  async onCreateTag() {
    console.log("🏷️ Create Tag clicked");
    await this.action.doAction("custom_documents.action_custom_document_tag_wizard", {
      onClose: () => this.model.load(),
    });
  }
}

/* -----------------------------
 *  KANBAN: controller
 * ----------------------------*/
class CustomDocumentKanbanController extends KanbanController {
  setup() {
    super.setup();
    this.action = useService("action");

    // Intercept anchor clicks inside kanban cards to avoid navigation
    this._blockCardAnchors = (ev) => {
      const anchor = ev.target.closest(".o_kanban_view .o_kanban_record a");
      if (!anchor) return;
      ev.preventDefault();
      ev.stopPropagation();
    };

    onMounted(() => {
      this.el?.addEventListener("click", this._blockCardAnchors, true);
      this.el?.addEventListener("dblclick", this._blockCardAnchors, true);
    });
    onWillUnmount(() => {
      this.el?.removeEventListener("click", this._blockCardAnchors, true);
      this.el?.removeEventListener("dblclick", this._blockCardAnchors, true);
    });
  }

  // Block opening a record from kanban card clicks, too
  async openRecord(/*record, options*/) {
    return; // no-op
  }

  _getCurrentFolderId() {
    if (this.props.context?.default_folder_id) {
      return this.props.context.default_folder_id;
    }
    const found = (this.props.domain || []).find(
      (d) =>
        Array.isArray(d) &&
        d[0] === "folder_id" &&
        (d[1] === "=" || d[1] === "child_of")
    );
    return found ? found[2] : false;
  }

  async onUploadFile() {
    const folderId = this._getCurrentFolderId();
    await this.action.doAction("custom_documents.action_custom_document_upload_file", {
      additionalContext: {
        default_document_type: "file",
        default_folder_id: folderId || false,
      },
    });
  }

  async onAddUrl() {
    const folderId = this._getCurrentFolderId();
    await this.action.doAction("custom_documents.action_custom_document_upload_url", {
      additionalContext: {
        default_document_type: "url",
        default_folder_id: folderId || false,
      },
    });
  }

  async onCreateFolder() {
    const folderId = this._getCurrentFolderId();
    await this.action.doAction("custom_documents.action_custom_document_folder_wizard", {
      additionalContext: {
        default_parent_id: folderId || false,
      },
    });
  }

  // Optional parity with list (in case you add a tag button in kanban header later)
  async onCreateTag() {
    await this.action.doAction("custom_documents.action_custom_document_tag_wizard", {
      onClose: () => this.model.load(),
    });
  }
}

// Register views with button template
export const customDocumentListView = {
  ...listView,
  Controller: CustomDocumentListController,
  buttonTemplate: "custom_documents.CustomDocumentListButtons",
};

export const customDocumentKanbanView = {
  ...kanbanView,
  Controller: CustomDocumentKanbanController,
};

registry.category("views").add("custom_document_list", customDocumentListView);
registry.category("views").add("custom_document_kanban", customDocumentKanbanView);

console.log("✓ Custom document views registered: rows/cards won't open records; tag wizard hooked.");
