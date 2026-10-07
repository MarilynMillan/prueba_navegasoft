import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (this.config.module_pos_restaurant && !this.initial_customer_count && this.customer_count > 0) {
            this.customer_count = 0;
            this.initial_customer_count = false;
        }
    },
});