/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },

    async submitOrder() {
        if (!this.currentOrder.start_time && this.pos.config.table_timer_enable){
            this.currentOrder.start_time = this.getUTCDateTime();
            this.currentOrder.end_time = false;
             // Add waiter name
            if (this.pos.get_cashier()) {
                this.currentOrder.waiter_name = this.pos.get_cashier().name;
            }
        }
        await super.submitOrder(...arguments);
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
});


patch(ProductScreen.prototype, {


    async submitOrder() {
        if (!this.currentOrder.start_time && this.pos.config.table_timer_enable){
            this.currentOrder.start_time = this.getUTCDateTime();
            this.currentOrder.end_time = false
        }
        await super.submitOrder(...arguments);
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
});
