import { Order } from "@pos_preparation_display/app/components/order/order";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    //OVERRIDE - Mantener orden original de comandeo (no ordenar por categoría)
    getSortedOrderlines() {
        return this.props.order.orderlines;
    }
});
