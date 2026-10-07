import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
	cashierHasPriceControlRights() {
		if(this.get_cashier()._is_restrict_price){
			return false
		}
		return !this.config.restrict_price_control || this.get_cashier()._role == "manager";
	},
	set_cashier(employee) {
        super.set_cashier(employee);
        if(this.get_cashier()._is_restrict_quantity){
        	this.numpadMode = "";
        }
    },
    cashMove(){
    	if(this.get_cashier()._is_restrict_cash_in_out){
    		this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso a la función de Ingreso/Salida de efectivo. Contacta a tu administrador."),
            });
    		return;
    	}
    	super.cashMove()
    },
    async onDeleteOrder(order) {
    	if(this.get_cashier()._is_restrict_cancel_order){
    		this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso para cancelar o retrasar el pedido. Contacta a tu administrador."),
            });
    		return;
    	}
    	return super.onDeleteOrder(...arguments);
    },
	async printReceipt(order) {
    	if(this.get_cashier()._is_restrict_print_order){
    		this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso para imprimir ordenes. Contacta a tu administrador."),
            });
    		return;
    	}
    	return super.printReceipt(...arguments);
    },

	async pay() {
    	if(this.get_cashier()._is_restrict_payment_order){
    		this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso para realizar el pago. Contacta a tu administrador."),
            });
    		return;
    	}
    	return super.pay(...arguments);
    },

	async selectPartner() {
    	if(this.get_cashier()._is_restrict_partner_order){
    		this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso para cambiar o agregar cliente a la orden. Contacta a tu administrador."),
            });
    		return;
    	}
    	return super.selectPartner(...arguments);
    },

	
});
