import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(TicketScreen.prototype, {
	async onDoRefund() {
        if (this.pos.get_cashier()._is_restrict_refund_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso a la solicitud de reembolso. Contacta a tu administrador."),
            });
    		return;
        }
        await super.onDoRefund(...arguments);
    },

	async _downloadInvoice() {
        if (this.pos.get_cashier()._is_restrict_reprintinvoice_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso para reimprimir factura. Contacta a tu administrador."),
            });
    		return;
        }
        await super._downloadInvoice(...arguments);
    },


});
