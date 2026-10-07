/*@odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { DenyPopup } from "../screens/popUps/deny_popUp";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";


patch(OrderSummary.prototype, {

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async confirm(selected_manager, state) {
        const manager = selected_manager.id;
        const cashier1 = this.pos.get_cashier().id;
        const session_id = this.pos.config.current_session_id.id;
        // const state = 'orderline_deleted';
        const receipt = this.pos.get_order().uid;
        const order_num = this.pos.get_order().trackingNumber;

        await this.orm.call("manager.approval", "getting_all_data", [{
            session_id,
            manager,
            cashier1,
            state,
            receipt,
            order_num
        }]);
    },

    async passwordPopup(manager, state){
        if (manager._pin == '') {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Unavailable Login Pin"),
                body: _t("Please create your login pin."),
            });
        }
        else {
            const payload = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Password?"),
                startingValue: '',
            });
            if (!payload) {
                return false;
            }
            else {
                if (manager._pin == Sha1.hash(payload)) {
                    this.confirm(manager, state);
                    return true;
                    // super.updateSelectedOrderline(...arguments);
                }
                else {
                    await this.env.services.dialog.add(AlertDialog, {
                        title: _t("Incorrect Password"),
                        body: _t("Please try again."),
                    });
                    return false;
                }
            }
        }
    },

    async updateSelectedOrderline({ buffer, key }) {
        if (this.pos.config.module_pos_restaurant && this.pos.config.module_pos_hr && this.pos.config.enable_pos_restaurant_restiction && this.pos.get_order().get_orderlines().length != 0 && this.pos.numpadMode == 'quantity') {
            var check = false;
            var state = '';
            var selected_orderline = this.pos.get_order().get_selected_orderline();
            if(this.pos.config.enable_restriction_on_orderline_delete && selected_orderline.qty==0 && key =="Backspace"){
                check = true;
                state = 'orderline_deleted'
            }
            else if(this.pos.config.enable_qty_update && selected_orderline.qty > 0){
                check = true;
                state = 'orderline_qty_update'
            }
            if (Object.keys(this.pos.get_order().last_order_preparation_change.lines).length != 0 && check) {
                var flag = 0;
                const dictOfdict = this.pos.get_order().last_order_preparation_change.lines;
                for (var key1 in dictOfdict) {
                    if (dictOfdict.hasOwnProperty(key1)) {
                        var innerObj = dictOfdict[key1];
                        if (innerObj.hasOwnProperty("product_id") && innerObj.product_id === selected_orderline.product_id.id) {
                            if (selected_orderline.qty <= innerObj.quantity || key === 'Backspace' || key < innerObj.qunatity) {
                                flag = 1;
                                break;
                            }
                        }
                    }
                }
                if (flag === 1) {
                    if (this.pos.cashier._role === 'cashier') {
                        const payload = await makeAwaitable(this.dialog, DenyPopup, {
                            title: _t("Unauthorised Action"),
                            body: _t("You are not authorized to do this action. Please take approval from manager.")
                        });
                        if (payload) {
                            const employeesList = this.pos.config.advanced_employee_ids;
                            if (!employeesList.length) {
                                await this.env.services.dialog.add(AlertDialog, {
                                    title: _t("Manager Not Available"),
                                    body: _t("Currently no any manager is available."),
                                });
                            }
                            const manager = await makeAwaitable(this.dialog, SelectionPopup, {
                                title: _t("Select Manager"),
                                list: employeesList.map((program) => ({
                                    id: program.id,
                                    item: program,
                                    label: program.name,
                                })),
                            });
        
                            if (!manager) {
                                return;
                            }
                            else {
                                if(await this.passwordPopup(manager, state)){
                                    super.updateSelectedOrderline(...arguments);
                                }
                            }
                        }
                    }
                    else {
                        if(await this.passwordPopup(this.pos.cashier, state)){
                            super.updateSelectedOrderline(...arguments);
                        }
                    }
                } else {
                    super.updateSelectedOrderline(...arguments);
                }
            }
            else {
                super.updateSelectedOrderline(...arguments);
            }

        } else {
            super.updateSelectedOrderline(...arguments);
        }

    },
});





