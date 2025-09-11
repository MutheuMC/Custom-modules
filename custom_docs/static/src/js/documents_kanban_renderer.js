import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { onMounted, onWillUnmount } from "@odoo/owl";

export class DocumentsKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        onMounted(() => {
            this.setupDragDrop();
        });
        
        onWillUnmount(() => {
            this.cleanupDragDrop();
        });
    }

    setupDragDrop() {
        const kanbanEl = this.rootRef.el;
        if (!kanbanEl) return;
        
        // Prevent default drag behaviors
        kanbanEl.addEventListener('dragover', this.onDragOver.bind(this));
        kanbanEl.addEventListener('dragleave', this.onDragLeave.bind(this));
        kanbanEl.addEventListener('drop', this.onDrop.bind(this));
        
        // Store references for cleanup
        this._dragOverHandler = this.onDragOver.bind(this);
        this._dragLeaveHandler = this.onDragLeave.bind(this);
        this._dropHandler = this.onDrop.bind(this);
    }

    cleanupDragDrop() {
        const kanbanEl = this.rootRef.el;
        if (!kanbanEl) return;
        
        kanbanEl.removeEventListener('dragover', this._dragOverHandler);
        kanbanEl.removeEventListener('dragleave', this._dragLeaveHandler);
        kanbanEl.removeEventListener('drop', this._dropHandler);
    }

    onDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        
        // Check if dragging files
        if (event.dataTransfer.types.includes('Files')) {
            event.dataTransfer.dropEffect = 'copy';
            
            // Add visual feedback
            const dropZone = event.currentTarget;
            dropZone.classList.add('o_documents_drag_over');
            
            // Create or update drop overlay
            if (!this.dropOverlay) {
                this.dropOverlay = document.createElement('div');
                this.dropOverlay.className = 'o_documents_drop_overlay';
                this.dropOverlay.innerHTML = `
                    <div class="o_documents_drop_content">
                        <i class="fa fa-cloud-upload fa-3x mb-3"></i>
                        <h3>${_t("Drop files here to upload")}</h3>
                        <p class="text-muted">${_t("Files will be uploaded to the current folder")}</p>
                    </div>
                `;
                dropZone.appendChild(this.dropOverlay);
            }
        }
    }

    onDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        
        // Remove visual feedback when leaving the drop zone
        const dropZone = event.currentTarget;
        if (dropZone && !dropZone.contains(event.relatedTarget)) {
            dropZone.classList.remove('o_documents_drag_over');
            if (this.dropOverlay) {
                this.dropOverlay.remove();
                this.dropOverlay = null;
            }
        }
    }

    async onDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        
        // Clean up visual feedback
        const dropZone = event.currentTarget;
        dropZone.classList.remove('o_documents_drag_over');
        if (this.dropOverlay) {
            this.dropOverlay.remove();
            this.dropOverlay = null;
        }
        
        // Get dropped files
        const files = event.dataTransfer.files;
        if (files.length === 0) return;
        
        // Get the folder from context or try to determine from drop location
        const context = this.props.list.context;
        let folderId = context.default_folder_id;
        
        // If dropped on a specific column, try to get that folder
        const columnEl = event.target.closest('.o_kanban_group');
        if (columnEl && this.props.list.groupByField === 'folder_id') {
            const groupId = columnEl.dataset.id;
            if (groupId) {
                folderId = parseInt(groupId);
            }
        }
        
        // Show uploading notification
        this.notification.add(
            _t(`Uploading ${files.length} file(s)...`),
            { type: "info" }
        );
        
        try {
            // Upload files
            for (const file of files) {
                await this._uploadFile(file, folderId);
            }
            
            this.notification.add(
                _t("Files uploaded successfully"),
                { type: "success" }
            );
            
            // Reload the view
            await this.props.list.model.load();
            
        } catch (error) {
            this.notification.add(
                _t("Error uploading files"),
                { type: "danger" }
            );
            console.error("Upload error:", error);
        }
    }

    async _uploadFile(file, folderId) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                const base64 = e.target.result.split(',')[1];
                
                try {
                    await this.rpc("/web/dataset/call_kw/documents.document/create", {
                        model: "documents.document",
                        method: "create",
                        args: [{
                            name: file.name,
                            datas: base64,
                            folder_id: folderId || false,
                            mimetype: file.type || 'application/octet-stream',
                            type: 'binary',
                        }],
                        kwargs: {},
                    });
                    resolve();
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
}