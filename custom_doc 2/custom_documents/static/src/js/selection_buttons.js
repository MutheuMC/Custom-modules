/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class SelectionButtons extends Component {
    static template = "custom_documents.SelectionButtons";
    static props = ["*"];
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }
    
    get hasSelection() {
        return this.env.model && 
               this.env.model.selection && 
               this.env.model.selection.size > 0;
    }
    
    get isCustomDocument() {
        return this.env.model && 
               this.env.model.resModel === 'custom.document';
    }
    
    get showButtons() {
        return this.isCustomDocument && this.hasSelection;
    }
    
    async onDownload() {
        if (!this.env.model || !this.env.model.selection) {
            return;
        }
        
        const selectedIds = [...this.env.model.selection];
        console.log("Download documents:", selectedIds);
        
        if (selectedIds.length !== 1) {
            this.notification.add(_t("Please select exactly one document."), { 
                type: "warning",
                sticky: false,
            });
            return;
        }
        
        try {
            const result = await this.orm.call(
                "custom.document", 
                "action_menu_download", 
                [selectedIds]
            );
            if (result) {
                await this.action.doAction(result);
            }
        } catch (error) {
            console.error("Download error:", error);
            this.notification.add(_t("Could not download the document."), { 
                type: "danger",
                sticky: false,
            });
        }
    }
    
    async onShare() {
        if (!this.env.model || !this.env.model.selection) {
            return;
        }
        
        const selectedIds = [...this.env.model.selection];
        console.log("Share documents:", selectedIds);
        
        if (selectedIds.length !== 1) {
            this.notification.add(_t("Please select exactly one document."), { 
                type: "warning",
                sticky: false,
            });
            return;
        }
        
        try {
            const result = await this.orm.call(
                "custom.document", 
                "action_menu_share", 
                [selectedIds]
            );
            if (result) {
                await this.action.doAction(result);
            }
        } catch (error) {
            console.error("Share error:", error);
            this.notification.add(_t("Could not share the document."), { 
                type: "danger",
                sticky: false,
            });
        }
    }
}

// Register the widget
registry.category("view_widgets").add("selection_buttons", SelectionButtons);

console.log("Selection buttons widget registered");