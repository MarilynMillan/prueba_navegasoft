/*@odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

// import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PosStore.prototype, {
    async confirm(selected_manager) {
        const manager = selected_manager.id;
        const cashier1 = this.cashier.id;
        const session_id = this.config.current_session_id.id;
        const state = 'session_close';

        await this.env.services.orm.call("manager.approval", "getting_all_data", [{
            session_id,
            manager,
            cashier1,
            state
        }]);
    },

    async closeSession() {
        var flag = 0;
        var last_flag = 0;
        var orders_map = this.data.records['pos.order'];
        var orders = Array.from(orders_map.values());

        if (this.config.enable_pos_restaurant_restiction && this.config.enable_restriction_on_session_close && this.config.module_pos_hr && this.config.module_pos_restaurant && orders.length > 0) {
            for (var i = 0; i < orders.length; i++) {
                if (orders[i].state === "draft") {
                    var manager = this.cashier;
                    if(manager.pin == ''){
                        flag = 1;
                        this.env.services.dialog.add(AlertDialog, {
                            title: _t("Unavailable Login Pin"),
                            body: _t("Please create your login pin."),
                        });
                    }
                    else{
                        const payload = await makeAwaitable(this.dialog, NumberPopup, {
                            formatDisplayedValue: (x) => x.replace(/./g, "•"),
                            title: _t("Password?"),
                            startingValue: '',
                        });
                        if (!payload) {
                            return;
                        }
                        else {
                            if (manager._pin == Sha1.hash(payload)) {
                                this.confirm(manager);
                                flag = 1;
                                last_flag = 1;
                                break;
                            }
                            else {
                                flag = 1;
                                await this.env.services.dialog.add(AlertDialog, {
                                    title: _t("Incorrect Password"),
                                    body: _t("Please try again."),
                                });
                            }
                        }
                    }
                }
            }
            if((flag == 1 && last_flag == 1) || (flag == 0 && last_flag == 0)){
                await super.closeSession(...arguments);
            }else{
                return;
            }  
             
        }
        else {
            super.closeSession(...arguments);
        }
    },
});
