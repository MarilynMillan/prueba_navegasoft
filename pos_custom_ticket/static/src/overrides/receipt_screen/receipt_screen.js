/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { OrderReceipt } from "@pos_custom_ticket/app/custom_receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen, {
  components: { OrderReceipt },
});

patch(ReceiptScreen.prototype, {
  async generateTicketImage(isBasicReceipt = false) {
    const order = this.pos.get_order();
    let invoiceId = order && order.raw ? order.raw.account_move : false;
    let receiptData = {
      data: this.pos.orderExportForPrinting(order),
      formatCurrency: this.env.utils.formatCurrency,
      orderUuid: order.uuid,
      basic_receipt: isBasicReceipt,
    };

    if (!invoiceId && order && typeof order.id === "number") {
      const [orderData] = await this.pos.data.read("pos.order", [order.id], [
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
    await this.renderer.toJpeg(OrderReceipt, {
      props: receiptData,
      addClass: "pos-receipt-print p-3",
    });
  },
});
