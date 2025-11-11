/** @odoo-module **/

import { SearchPanel } from "@web/search/search_panel/search_panel";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(SearchPanel.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    // Virtual buckets for each model
    getVirtualFolders() {
        const model = this.env.config.resModel;
        if (model === "custom.document") {
            return [
                { id: "my_drive",       name: "My Drive",        icon: "fa-home",      filter: "my_drive" },
                { id: "shared_with_me", name: "Shared with Me",   icon: "fa-users",     filter: "shared_with_me" },
                { id: "recent",         name: "Recent",           icon: "fa-clock-o",   filter: "recent" },
                { id: "starred",        name: "Starred",          icon: "fa-star",      filter: "starred" },
                { id: "trash",          name: "Trash",            icon: "fa-trash",     filter: "trash" },
            ];
        }
        if (model === "custom.document.folder") {
            return [
                { id: "my_folders",     name: "My Folders",      icon: "fa-home",      filter: "my_folders" },
                { id: "shared_folders", name: "Shared Folders",  icon: "fa-share-alt", filter: "shared_folders" },
                { id: "root_folders",   name: "Root Folders",    icon: "fa-sitemap",   filter: "root_folders" },
            ];
        }
        return [];
    },

    // Highlight active virtual filter
    getActiveVirtualFolder() {
        const active = this.env.searchModel.getSearchItems(i => i.type === "filter" && i.checked);
        const vf = this.getVirtualFolders();
        for (const it of active) {
            const match = vf.find(v => v.filter === it.name);
            if (match) return match.id;
        }
        return null;
    },

    // Ensure only one virtual filter at a time
    onVirtualFolderClick(_id, filterName) {
        if (!filterName) return;
        const vfNames = this.getVirtualFolders().map(v => v.filter);
        const items = this.env.searchModel.getSearchItems(i => i.type === "filter" && vfNames.includes(i.name));

        // turn off others
        for (const it of items) {
            if (it.name !== filterName && it.checked) {
                this.env.searchModel.toggleSearchItem(it.id);
            }
        }
        // toggle target
        const target = items.find(i => i.name === filterName);
        if (target) {
            this.env.searchModel.toggleSearchItem(target.id);
        }
    },
});
