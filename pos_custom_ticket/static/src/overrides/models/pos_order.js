/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
  export_for_printing(baseUrl, headerData) {
    return {
        ...super.export_for_printing(...arguments),
        customer: this.get_partner(),
        posbox: this.config.name
    }
  },
});
