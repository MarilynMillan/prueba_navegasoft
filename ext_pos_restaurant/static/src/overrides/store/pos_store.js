import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { add as addGuestDialog } from "@ext_pos_restaurant/models/guest_dialog";

patch(PosStore.prototype, {
    showScreen(name, props) {
        super.showScreen(name, props);
        if (name == 'ProductScreen' && this.config.module_pos_restaurant) {
            const order = this.get_order();
            console.log(order);
            console.log(order.initial_customer_count);
            console.log(order.customer_count);
            if (!order || order.initial_customer_count || order.customer_count > 0) return;
            addGuestDialog(this, order);
        }
        return true;
    }
});