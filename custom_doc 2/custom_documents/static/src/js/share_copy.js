/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * Client action to copy text to clipboard
 * Called from share wizard buttons
 */
registry.category("actions").add("custom_documents.copy_to_clipboard", async (env, params) => {
    const notify = env.services.notification;
    const text = (params && params.text) || "";
    const title = (params && params.notificationTitle) || "Copied to clipboard";

    if (!text) {
        notify.add("No text to copy", { type: "warning" });
        return;
    }

    /**
     * Fallback copy method for older browsers
     */
    async function fallbackCopy(textToCopy) {
        const textarea = document.createElement("textarea");
        textarea.value = textToCopy;
        textarea.style.position = "fixed";
        textarea.style.top = "-9999px";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        
        try {
            textarea.select();
            textarea.setSelectionRange(0, 99999); // For mobile devices
            document.execCommand("copy");
        } finally {
            document.body.removeChild(textarea);
        }
    }

    try {
        // Try modern clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers or insecure contexts
            await fallbackCopy(text);
        }
        
        notify.add(title, { 
            type: "success",
            sticky: false,
        });
        
    } catch (error) {
        console.error("Copy to clipboard failed:", error);
        notify.add("Could not copy to clipboard. Please copy manually.", { 
            type: "warning",
            sticky: true,
        });
    }
});

console.log("✓ Copy to clipboard client action registered");