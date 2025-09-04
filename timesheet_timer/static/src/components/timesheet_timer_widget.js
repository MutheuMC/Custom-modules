/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

export class TimesheetTimerWidget extends Component {
    static template = "timesheet_timer.TimerWidget";
    static components = { FloatTimeField };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            isRunning: false,
            currentTime: 0,         // hours (float)
            displayTime: "00:00:00",
            intervalId: null,
        });

        onWillStart(async () => {
            await this._initFromRecord();
        });

        onMounted(() => {
            this._maybeStartTicker();
        });

        onWillUnmount(() => {
            this._clearTicker();
        });
    }

    async _initFromRecord() {
        const record = this.props.record;
        if (!record || !record.data) return;

        const d = record.data;
        this.state.isRunning = !!d.is_timer_running;
        this.state.currentTime = d.unit_amount || 0;

        if (this.state.isRunning && d.timer_start) {
            // compute (timer_pause + elapsed) in hours
            const start = new Date(d.timer_start);
            const now = new Date();
            const elapsedHours = (now - start) / 1000 / 3600;
            this.state.currentTime = (d.timer_pause || 0) + elapsedHours;
        }
        this._updateDisplay();
    }

    _maybeStartTicker() {
        if (this.state.isRunning) {
            this._startTicker();
        }
    }

    _startTicker() {
        if (this.state.intervalId) clearInterval(this.state.intervalId);
        this.state.intervalId = setInterval(() => {
            if (!this.state.isRunning) return;
            this.state.currentTime += 1 / 3600; // +1 second
            this._updateDisplay();
        }, 1000);
    }

    _clearTicker() {
        if (this.state.intervalId) {
            clearInterval(this.state.intervalId);
            this.state.intervalId = null;
        }
    }

    _updateDisplay() {
        const totalSeconds = Math.floor((this.state.currentTime || 0) * 3600);
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;
        this.state.displayTime = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    async onTimerClick() {
        try {
            const record = this.props.record;
            if (!record || !record.resId) {
                this.notification.add("Please save the record before using the timer.", { type: "warning" });
                return;
            }

            if (this.state.isRunning) {
                await this._stopTimer(record.resId);
            } else {
                await this._startTimer(record.resId);
            }
        } catch (err) {
            console.error("Timer error", err);
            this.notification.add("Error with timer operation.", { type: "danger" });
        }
    }

    async _startTimer(resId) {
        // Correct call: pass the ID as a list to the record method
        await this.orm.call("account.analytic.line", "action_timer_start", [[resId]]);
        this.state.isRunning = true;
        this._startTicker();
        await this._reloadRecord();
        this.notification.add("Timer started.", { type: "success" });
    }

    async _stopTimer(resId) {
        // Correct call: pass the ID as a list to the record method
        await this.orm.call("account.analytic.line", "action_timer_stop", [[resId]]);
        this.state.isRunning = false;
        this._clearTicker();
        await this._reloadRecord();
        this.notification.add("Timer stopped.", { type: "success" });
    }

    async _reloadRecord() {
        try {
            if (this.props.record.load) {
                await this.props.record.load();
            } else if (this.props.record?.model?.root?.load) {
                await this.props.record.model.root.load();
            }
        } catch (_e) {
            // non-fatal
        }
        await this._initFromRecord();
    }

    get buttonClass() {
        return this.state.isRunning ? "btn-danger" : "btn-primary";
    }
    get buttonIcon() {
        return this.state.isRunning ? "fa-stop" : "fa-play";
    }
    get buttonTitle() {
        return this.state.isRunning ? "Stop Timer" : "Start Timer";
    }
}

TimesheetTimerWidget.props = {
    ...FloatTimeField.props,
};

TimesheetTimerWidget.supportedTypes = ["float"];

// Register the widget as a field widget called "timesheet_timer"
registry.category("fields").add("timesheet_timer", { component: TimesheetTimerWidget });