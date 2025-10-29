/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("actions").add("custom_documents.copy_to_clipboard", async (env, params) => {
    const notify = env.services.notification;
    const text = (params && params.text) || "";

    async function fallbackCopy(t) {
        const ta = document.createElement("textarea");
        ta.value = t;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); } finally { document.body.removeChild(ta); }
    }

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
        } else {
            await fallbackCopy(text);
        }
        notify.add(params.notificationTitle || "Copied to clipboard", { type: "success" });
    } catch (e) {
        notify.add("Could not copy to clipboard", { type: "warning" });
    }
});
