/** @odoo-module **/
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Add hover action buttons (Share, Download, Info) to document list rows
 */
patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    },

    /**
     * Add hover buttons after rendering
     */
    onMounted() {
        super.onMounted(...arguments);
        if (this.props.list?.resModel === 'custom.document') {
            this._addDocumentHoverButtons();
        }
    },

    /**
     * Re-add buttons after updates
     */
    async onPatched() {
        await super.onPatched(...arguments);
        if (this.props.list?.resModel === 'custom.document') {
            this._addDocumentHoverButtons();
        }
    },

    /**
     * Add hover action buttons to each document row
     */
    _addDocumentHoverButtons() {
        const listEl = this.rootRef?.el;
        if (!listEl || !listEl.classList.contains('custom_document_list')) {
            return;
        }

        const rows = listEl.querySelectorAll('tbody tr.o_data_row');
        
        rows.forEach((row, index) => {
            // Skip if buttons already added
            if (row.querySelector('.o_document_hover_actions')) {
                return;
            }

            const record = this.props.list.records[index];
            if (!record) return;

            const docId = record.resId;

            // Create actions container
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'o_document_hover_actions';
            
            // Share button
            const shareBtn = this._createActionButton('fa-share-alt', 'Share', () => {
                this._onShareDocument(docId);
            });
            
            // Download button
            const downloadBtn = this._createActionButton('fa-download', 'Download', () => {
                this._onDownloadDocument(docId);
            });
            
            // Info button
            const infoBtn = this._createActionButton('fa-info-circle', 'Info & Tags', () => {
                this._onInfoDocument(docId);
            });

            actionsDiv.appendChild(shareBtn);
            actionsDiv.appendChild(downloadBtn);
            actionsDiv.appendChild(infoBtn);

            // Insert at the end of the row
            const lastCell = row.querySelector('td:last-child');
            if (lastCell) {
                lastCell.style.position = 'relative';
                lastCell.appendChild(actionsDiv);
            }
        });
    },

    /**
     * Create a single action button
     */
    _createActionButton(iconClass, title, onClick) {
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-link o_document_hover_btn';
        btn.title = title;
        btn.type = 'button';
        btn.innerHTML = `<i class="fa ${iconClass}"></i>`;
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            onClick();
        });
        return btn;
    },

    /**
     * Handle Share action
     */
    async _onShareDocument(docId) {
        try {
            const result = await this.orm.call(
                'custom.document',
                'action_menu_share',
                [[docId]]
            );
            if (result) {
                await this.action.doAction(result);
            }
        } catch (error) {
            console.error('Share error:', error);
            this.notification.add('Could not open share dialog', { type: 'danger' });
        }
    },

    /**
     * Handle Download action
     */
    async _onDownloadDocument(docId) {
        try {
            const result = await this.orm.call(
                'custom.document',
                'action_menu_download',
                [[docId]]
            );
            if (result && result.type === 'ir.actions.act_url') {
                window.location.href = result.url;
            }
        } catch (error) {
            console.error('Download error:', error);
            this.notification.add('Could not download document', { type: 'danger' });
        }
    },

    /**
     * Handle Info action
     */
    async _onInfoDocument(docId) {
        try {
            const result = await this.orm.call(
                'custom.document',
                'action_menu_info_tags',
                [[docId]]
            );
            if (result) {
                await this.action.doAction(result);
            }
        } catch (error) {
            console.error('Info error:', error);
            this.notification.add('Could not open info dialog', { type: 'danger' });
        }
    },
});

console.log("✓ Document list hover actions registered");