import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import {onMounted} from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

patch(ControlButtons.prototype, {

    setup() {
        super.setup(...arguments);
        onMounted(() => {

            if (this.pos.get_cashier()._is_restrict_actiondiscount) {
                let js_discount = document.getElementsByClassName('js_discount');
                (js_discount.length > 0) && (js_discount[0].disabled = true);
            }
            const botones = document.querySelectorAll('.btn.btn-secondary.btn-lg.py-5');
            if (this.pos.get_cashier()._is_restrict_transfer) {
		botones.forEach(boton => {
    			if (boton.textContent.includes('Transferir')) {
        		boton.disabled = true;
    			}
	    	});
	    }
           

        });
    },

    async clickRefund() {
        if (this.pos.get_cashier()._is_restrict_refund_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso a la solicitud de reembolso. Contacta a tu administrador."),
            });
    		return;
        }

        const order = this.pos.get_order();
        const partner = order.get_partner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.pos.showScreen("TicketScreen", {
            stateOverride: {
                filter: "SYNCED",
                search: searchDetails,
                destinationOrder: order,
            },
        });
        
    },

    async clickPricelist() {
        if (this.pos.get_cashier()._is_restrict_pricelist_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error de acceso"),
                body: _t("No tienes acceso a la lista de precios. Contacta a tu administrador."),
            });
    		return;
        }

        const selectionList = this.pos.models["product.pricelist"].map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected:
                this.currentOrder.pricelist_id &&
                pricelist.id === this.currentOrder.pricelist_id.id,
            item: pricelist,
        }));

        if (!this.pos.config.pricelist_id) {
            selectionList.push({
                id: null,
                label: _t("Default Price"),
                isSelected: !this.currentOrder.pricelist_id,
                item: null,
            });
        }

        const payload = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Select the pricelist"),
            list: selectionList,
        });

        if (payload) {
            this.pos.selectPricelist(payload);
        }
        
    },

});
