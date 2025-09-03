/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";

import { useComponent, onMounted, onWillUnmount, useState } from "@odoo/owl";

// Custom widget to handle the timesheet timer functionality.
export class TimesheetTimerWidget extends Component {
    static template = 'timesheet_timer.TimerWidget';
    static props = {
        record: { type: Object },
    };

    setup() {
        this.rpc = useService("rpc");
        this.popover = usePopover();
        this.state = useState({
            isRunning: this.props.record.data.is_running,
            timeSpent: this.props.record.data.unit_amount * 3600, // Convert hours to seconds
            interval: null,
        });

        onMounted(() => {
            if (this.state.isRunning) {
                this.startTimer();
            }
        });

        onWillUnmount(() => {
            this.clearTimer();
        });
    }

    // Helper function to format time as HH:MM:SS
    formatTime(totalSeconds) {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = Math.floor(totalSeconds % 60);
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    // Starts the timer.
    async startTimer() {
        try {
            await this.rpc('/web/dataset/call_kw/account.analytic.line/start_timer', {
                model: 'account.analytic.line',
                method: 'start_timer',
                args: [this.props.record.resId],
                kwargs: {},
            });

            this.state.isRunning = true;
            this.state.interval = setInterval(() => {
                this.state.timeSpent += 1;
            }, 1000);
        } catch (error) {
            console.error('Error starting timer:', error);
        }
    }

    // Stops the timer.
    async stopTimer() {
        this.clearTimer();
        try {
            await this.rpc('/web/dataset/call_kw/account.analytic.line/stop_timer', {
                model: 'account.analytic.line',
                method: 'stop_timer',
                args: [this.props.record.resId],
                kwargs: {},
            });
            this.state.isRunning = false;
        } catch (error) {
            console.error('Error stopping timer:', error);
        }
    }

    // Clears the interval timer.
    clearTimer() {
        if (this.state.interval) {
            clearInterval(this.state.interval);
            this.state.interval = null;
        }
    }

    // Handles the button click event.
    onClick() {
        if (this.state.isRunning) {
            this.stopTimer();
        } else {
            this.startTimer();
        }
    }
}

// Register the custom timesheet timer widget.
registry.category("fields").add("timesheet_timer", TimesheetTimerWidget);
