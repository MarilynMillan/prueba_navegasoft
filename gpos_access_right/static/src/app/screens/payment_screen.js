/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    shouldDownloadInvoice() {
        return Boolean(this.pos.config.allow_pdf_download && this.currentOrder?.is_to_invoice());
    },
});
