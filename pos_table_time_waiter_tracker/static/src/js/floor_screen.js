/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(FloorScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.tableTimers = {};
        this.state.tableWaiters = {};
        this.state.tableAmounts = {};  // For order amounts
        this.timer = null;
        if (this.pos.config.table_timer_enable) {
            onMounted(() => this.startTimer());
            onWillUnmount(() => this.stopTimer());
        }
    },

    startTimer() {
        this.timer = setInterval(() => {
            this.updateTimers();
        }, 1000);
    },

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    },

    updateTimers() {
        const objTimers = {};
        const objWaiters = {};
        const objAmounts = {};  // For order amounts

        if (this.activeTables) {
            this.activeTables.forEach((table) => {
                const tableId = table.id;
                const orders = this.pos.getTableOrders(tableId);

                if (orders.length) {
                    // Store waiter name
                    if (orders[0].waiter_name) {
                        objWaiters[tableId] = orders[0].waiter_name;
                    }

                    // Store order amount
                    if (orders[0].amount_total) {
                        objAmounts[tableId] = orders[0].amount_total;
                    }

                    // Calculate timer
                    if (orders[0].start_time && !orders[0].end_time) {
                        const start = new Date(orders[0].start_time.replace(" ", "T") + "Z");
                        const end = new Date(this.getUTCDateTime().replace(" ", "T") + "Z");
                        const diffMs = end - start;
                        const hours = String(Math.floor(diffMs / (1000 * 60 * 60))).padStart(2, '0');
                        const minutes = String(Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))).padStart(2, '0');
                        const seconds = String(Math.floor((diffMs % (1000 * 60)) / 1000)).padStart(2, '0');
                        objTimers[tableId] = `${hours}:${minutes}:${seconds}`;
                    } else {
                        objTimers[tableId] = "";
                    }
                } else {
                    objTimers[tableId] = "";
                }
            });
        }

        Object.assign(this.state.tableTimers, objTimers);
        Object.assign(this.state.tableWaiters, objWaiters);
        Object.assign(this.state.tableAmounts, objAmounts);
    },

    getUTCDateTime() {
        const now = new Date();
        const year = now.getUTCFullYear();
        const month = String(now.getUTCMonth() + 1).padStart(2, '0');
        const date = String(now.getUTCDate()).padStart(2, '0');
        const hours = String(now.getUTCHours()).padStart(2, '0');
        const minutes = String(now.getUTCMinutes()).padStart(2, '0');
        const seconds = String(now.getUTCSeconds()).padStart(2, '0');
        return `${year}-${month}-${date} ${hours}:${minutes}:${seconds}`;
    },

    getTableTimer(table) {
        return this.state.tableTimers[table.id] || "";
    },

    getTableWaiter(table) {
        return this.state.tableWaiters[table.id] || "";
    },

    getTableAmount(table) {
        const amount = this.state.tableAmounts[table.id] || 0;
        return this.env.utils.formatCurrency(amount);
    },
});