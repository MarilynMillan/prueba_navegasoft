/** @odoo-module **/

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";
import { OrderReceipt } from "@pos_custom_ticket/app/custom_receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
  async clickPrintBill() {
    // Need to await to have the result in case of automatic skip screen.
    const order = this.pos.get_order();
    let invoiceId = order.raw.account_move;
    let receiptData = {
      data: this.pos.orderExportForPrinting(order),
      formatCurrency: this.env.utils.formatCurrency,
      orderUuid: order.uuid,
    };

    if (!invoiceId) {
      const invoice = await this.pos.data.orm.searchRead(
        "account.move",
        [["ref", "=", order.name]],
        ["id"]
      );
      invoiceId = invoice.length ? invoice[0].id : false;
    }
    if (invoiceId) {
      const dianValues = await this.data.call(
        "account.move",
        "l10n_co_dian_get_extra_invoice_report_values",
        [invoiceId]
      );
      receiptData.dianValues = dianValues || {};
    }
    (await this.printer.print(OrderReceipt, receiptData)) ||
      this.dialog.add(BillScreen);
  },
});
