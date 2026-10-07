/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@pos_custom_ticket/app/custom_receipt/order_receipt";

patch(PosStore.prototype, {
  async printReceipt({
    basic = false,
    order = this.get_order(),
    printBillActionTriggered = false,
  } = {}) {
    let invoiceId = order && order.raw ? order.raw.account_move : false;
    let receiptData = {
      data: this.orderExportForPrinting(order),
      formatCurrency: this.env.utils.formatCurrency,
      orderUuid: order.uuid,
      basic_receipt: basic,
    };

    if (!invoiceId && order && typeof order.id === "number") {
      const [orderData] = await this.data.read("pos.order", [order.id], [
        "account_move",
      ]);
      invoiceId = orderData?.account_move || false;
    }

    if (invoiceId) {
      const dianValues = await this.data.call(
        "account.move",
        "l10n_co_dian_get_extra_invoice_report_values",
        [invoiceId]
      );
      receiptData.dianValues = dianValues || {};
    }
    await this.printer.print(OrderReceipt, receiptData, {
      webPrintFallback: true,
    });
    if (!printBillActionTriggered) {
      const nbrPrint = order.nb_print;
      await this.data.write("pos.order", [order.id], {
        nb_print: nbrPrint + 1,
      });
    }
    return true;
  },
});
