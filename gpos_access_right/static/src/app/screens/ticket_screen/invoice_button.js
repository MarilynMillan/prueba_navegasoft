/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";


patch(InvoiceButton.prototype, {
    setup() {
        super.setup(...arguments);
    },
    async _downloadInvoice(orderId) {

      if (this.pos.get_cashier()._is_restrict_reprintinvoice_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso a reimprimir facturas. Contacta a tu administrador."),
            });
    		return;
        }
      
        try {
            const orderWithInvoice = await this.pos.data.read("pos.order", [orderId], [], {
                load: false,
            });
            const order = orderWithInvoice[0];
            const accountMoveId = order.raw.account_move;
            if (accountMoveId) {
                await this.invoiceService.downloadPdf(accountMoveId);
            }
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            } else {
                // NOTE: error here is most probably undefined
                this.dialog.add(AlertDialog, {
                    title: _t("Network Error"),
                    body: _t("Unable to download invoice."),
                });
            }
        }
    }
});
