/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ReloadCurrentAction extends Component {
    static template = "custom_documents.ReloadCurrentAction";

    setup() {
        this.action = useService("action");
        onMounted(async () => {
            // Programmatic view refresh (no full page reload)
            await this.action.doAction({ type: "ir.actions.client", tag: "reload" });
        });
    }
}

registry.category("actions").add("custom_documents.reload_current", ReloadCurrentAction);
