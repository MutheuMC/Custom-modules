/** @odoo-module **/
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

/**
 * Patch ListRenderer to add email data attributes for share people list
 * This allows CSS to display email below name in card-style layout
 */
patch(ListRenderer.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
    },

    /**
     * After rendering, add email data attributes to share list items
     */
    async onWillUpdateProps(nextProps) {
        await super.onWillUpdateProps(...arguments);
        this._addEmailAttributes();
    },

    /**
     * Add email as data attribute after initial render
     */
    onMounted() {
        super.onMounted(...arguments);
        this._addEmailAttributes();
    },

    /**
     * Helper: Add email data attributes to list rows
     */
    _addEmailAttributes() {
        // Only process share people list
        if (!this.props.list?.resModel === 'custom.document.share.line') {
            return;
        }

        const listEl = this.rootRef?.el;
        if (!listEl || !listEl.classList.contains('o_share_people_list')) {
            return;
        }

        // Process each row
        const rows = listEl.querySelectorAll('tbody tr.o_data_row');
        rows.forEach((row, index) => {
            const record = this.props.list.records[index];
            if (!record) return;

            // Get email value
            const email = record.data.email || '';
            
            // Find the many2one_avatar span and add email as data attribute
            const avatarSpan = row.querySelector('.o_m2o_avatar > span:not(.o_avatar)');
            if (avatarSpan && email) {
                avatarSpan.setAttribute('data-email', email);
            }
        });
    },
});

console.log("✓ Share list renderer patched for email display");