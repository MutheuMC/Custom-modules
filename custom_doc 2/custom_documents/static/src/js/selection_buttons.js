/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SelectionPanel } from "@web/views/selection_panel/selection_panel";
import { useService } from "@web/core/utils/hooks";

patch(SelectionPanel.prototype, "custom_documents.selection_buttons", {
    setup() {
        // keep original behavior
        this._super && this._super(...arguments);
        // services
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    },

    /**
     * Small helper to call a model method on the current selection.
     * Only works for the custom.document list; otherwise noop.
     */
    async _call(methodName) {
        try {
            const resModel = this.props?.resModel || this.env?.config?.action?.resModel;
            if (resModel !== "custom.document") return; // do nothing on other models
            const ids = Array.from(this.props?.selection || []);
            if (ids.length !== 1) {
                this.notification.add(this.env._t("Select exactly one document."), { type: "warning" });
                return;
            }
            const res = await this.orm.call("custom.document", methodName, [ids]);
            if (res) {
                await this.action.doAction(res);
            }
        } catch (e) {
            // never crash the webclient
            console.error("custom_documents selection buttons error:", e);
            this.notification.add(this.env._t("Could not run the action."), { type: "danger" });
        }
    },

    async onDownloadClick() {
        await this._call("action_menu_download");
    },

    async onShareClick() {
        await this._call("action_menu_share");
    },
});
