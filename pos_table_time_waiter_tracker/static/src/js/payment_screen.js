/* @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
         if (this.pos.config.table_timer_enable && this.currentOrder.start_time){
             const end_time = this.getUTCDateTime()
             const start = new Date(this.currentOrder.start_time.replace(" ", "T") + "Z");
             const end = new Date(end_time.replace(" ", "T") + "Z");

                // Calculate the difference in milliseconds
             const diffMs = end - start;
             this.currentOrder.update({ end_time: end_time, duration: diffMs / (1000 * 60 * 60)});
         }
        await super.validateOrder(...arguments);
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
