/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class UploadDialog extends Component {
    static template = "custom_documents.UploadDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        onUpload: Function,
        folderId: { type: Number, optional: true },
    };

    setup() {
        this.notification = useService("notification");
    }

    async onFileChange(ev) {
        const files = ev.target.files;
        if (files.length > 0) {
            for (const file of files) {
                await this.uploadFile(file);
            }
            this.props.close();
        }
    }

    async uploadFile(file) {
        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64 = e.target.result.split(',')[1];
            await this.props.onUpload({
                name: file.name,
                file: base64,
                file_name: file.name,
                mimetype: file.type,
                document_type: 'file',
                folder_id: this.props.folderId,
            });
            this.notification.add(_t("File uploaded successfully"), {
                type: "success",
            });
        };
        reader.readAsDataURL(file);
    }
}

export class FolderDialog extends Component {
    static template = "custom_documents.FolderDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        onSave: Function,
        parentId: { type: Number, optional: true },
    };

    setup() {
        this.state = {
            name: "",
        };
    }

    async save() {
        if (this.state.name) {
            await this.props.onSave({
                name: this.state.name,
                parent_id: this.props.parentId,
            });
            this.props.close();
        }
    }

    discard() {
        this.props.close();
    }
}

export class UrlDialog extends Component {
    static template = "custom_documents.UrlDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        onSave: Function,
        folderId: { type: Number, optional: true },
    };

    setup() {
        this.state = {
            url: "",
            name: "",
        };
    }

    async add() {
        if (this.state.url) {
            await this.props.onSave({
                url: this.state.url,
                name: this.state.name || this.state.url.split('/').pop() || 'URL Document',
                document_type: 'url',
                folder_id: this.props.folderId,
            });
            this.props.close();
        }
    }

    discard() {
        this.props.close();
    }
}

export class DocumentDropdown extends Component {
    static template = "custom_documents.DocumentDropdown";
    static props = {
        folderId: { type: Number, optional: true },
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async onUpload() {
        this.dialog.add(UploadDialog, {
            folderId: this.props.folderId,
            onUpload: async (data) => {
                await this.orm.create("custom.document", [data]);
                await this.action.doAction({
                    type: "ir.actions.client",
                    tag: "reload",
                });
            },
        });
    }

    async onRequest() {
        // Placeholder for request functionality
        this.dialog.add(Dialog, {
            title: _t("Request Document"),
            body: _t("Request functionality will be implemented later."),
        });
    }

    async onLink() {
        this.dialog.add(UrlDialog, {
            folderId: this.props.folderId,
            onSave: async (data) => {
                await this.orm.create("custom.document", [data]);
                await this.action.doAction({
                    type: "ir.actions.client",
                    tag: "reload",
                });
            },
        });
    }

    async onSpreadsheet() {
        // Placeholder for spreadsheet functionality
        this.dialog.add(Dialog, {
            title: _t("Create Spreadsheet"),
            body: _t("Spreadsheet functionality will be implemented later."),
        });
    }

    async onFolder() {
        this.dialog.add(FolderDialog, {
            parentId: this.props.folderId,
            onSave: async (data) => {
                await this.orm.create("custom.document.folder", [data]);
                await this.action.doAction({
                    type: "ir.actions.client",
                    tag: "reload",
                });
            },
        });
    }
}