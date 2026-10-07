/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {

    setup() {
        super.setup(...arguments);
        if (this.config.pos_customer_id && !this.finalized) {
            this.set_partner(this.config.pos_customer_id);
        }
        if (this.config.pos_invoice_default) {
             this.to_invoice=true;
        }
         
       
        },
    
});
