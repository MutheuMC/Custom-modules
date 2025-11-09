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

    // Debug logging
    console.log("📋 Copy to clipboard called");
    console.log("  Text length:", text.length);
    console.log("  Text preview:", text.substring(0, 100));
    console.log("  Full params:", params);

    if (!text || text.trim() === "") {
        console.error("❌ No text provided to copy");
        notify.add("No text to copy. Please check your share settings.", { 
            type: "warning",
            sticky: true,
        });
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
            const success = document.execCommand("copy");
            console.log("  Fallback copy success:", success);
            return success;
        } finally {
            document.body.removeChild(textarea);
        }
    }

    try {
        // Try modern clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            console.log("  Using modern clipboard API");
            await navigator.clipboard.writeText(text);
            console.log("✅ Copy successful (modern API)");
        } else {
            // Fallback for older browsers or insecure contexts
            console.log("  Using fallback copy method");
            await fallbackCopy(text);
            console.log("✅ Copy successful (fallback)");
        }
        
        notify.add(title, { 
            type: "success",
            sticky: false,
        });
        
    } catch (error) {
        console.error("❌ Copy to clipboard failed:", error);
        console.error("  Error details:", error.message);
        
        // Show manual copy dialog as last resort
        notify.add(
            `Could not copy automatically. Please copy manually:\n\n${text}`, 
            { 
                type: "warning",
                sticky: true,
            }
        );
    }
});

console.log("✓ Copy to clipboard client action registered (with debug)");