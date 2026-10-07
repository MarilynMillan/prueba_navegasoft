/*@odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { patch } from "@web/core/utils/patch";
import { DenyPopup } from "../screens/popUps/deny_popUp";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PosStore.prototype, {

    async confirm1(selected_manager) {
        const manager = selected_manager.id;
        const cashier1 = this.cashier.id;
        const session_id = this.config.current_session_id.id;
        const state = 'order_deleted';

        await this.env.services.orm.call("manager.approval", "getting_all_data", [{
            session_id,
            manager,
            cashier1,
            state,
        }]);
    },

    async onDeleteOrder(order) {
        
        if (this.config.enable_pos_restaurant_restiction && this.config.enable_restriction_on_order_delete && this.config.module_pos_hr && this.config.module_pos_restaurant && Object.keys(order.last_order_preparation_change.lines).length) {
                if(this.cashier._role == 'cashier'){
                    const payload = await makeAwaitable(this.dialog, DenyPopup, {
                        title: _t("Unauthorised Action"),
                        body: _t("You are not authorized to delete the order. Please take approval from manager.")
                    });
                    if (payload) {
                        const employeesList = this.config.advanced_employee_ids;
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
                            if(manager._pin == ''){
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
                                        this.confirm1(manager);
                                        await super.onDeleteOrder(...arguments);
                                    }
                                    else {
                                        await this.env.services.dialog.add(AlertDialog, {
                                            title: _t("Incorrect Password"),
                                            body: _t("Please try again."),
                                        });
                                    }
                                }
                            }
                        }
                    }
                }
                else{
                    var manager = this.cashier;
                    if(manager._pin == ''){
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
                                this.confirm1(manager);
                                await super.onDeleteOrder(...arguments);
                            }
                            else {
                                await this.env.services.dialog.add(AlertDialog, {
                                    title: _t("Incorrect Password"),
                                    body: _t("Please try again."),
                                });
                            }
                        }
                    }
                }
        }
        else {
            await super.onDeleteOrder(...arguments);
        }
    },
});
