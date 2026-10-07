/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
  getDisplayData() {
    return {
      ...super.getDisplayData(),
      product_id: this.product_id.id,
    };
  },
});
