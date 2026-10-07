/** @odoo-module **/

import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";
import { Dialog } from "@web/core/dialog/dialog";
import { OrderReceipt } from "@pos_custom_ticket/app/custom_receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(BillScreen, {
  components: { OrderReceipt, Dialog },
});
