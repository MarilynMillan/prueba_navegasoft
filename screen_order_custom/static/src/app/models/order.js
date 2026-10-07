import { Order } from "@pos_preparation_display/app/models/order";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(order) {
        super.setup(order);
        this.waiter_name = order.waiter_name || '';
    }
});
