/** @odoo-module **/

import { registry } from "@web/core/registry";

const actionRegistry = registry.category("actions");


function reloadDocumentsView(env, action) {
    const actionService = env.services.action;
    const ctx = action.context || {};

    // Try to keep current folder filter if provided
    const folderId =
        ctx.search_default_folder_id ||
        ctx.default_folder_id ||
        ctx.folder_id ||
        false;

    const additionalContext = {};
    if (folderId) {
        additionalContext.search_default_folder_id = folderId;
    }

    // Re-open the main Documents action, but only in the action area
    return actionService.doAction("custom_documents.action_custom_document", {
        additionalContext,
        replaceLastAction: true,
    });
}

actionRegistry.add("reload_documents_view", reloadDocumentsView);
