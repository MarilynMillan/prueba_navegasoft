/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import {  makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
// import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useService } from "@web/core/utils/hooks";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.pos = usePos();
        this.sh_start();
    },

    async askPin(employee) {
        const self= this;
        const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
            //isPassword: true,
            title: _t("Password ?"),
            //startingValue: null,

        })
        // await this.dialog.add(NumberPopup, {
        //     isPassword: true,
        //     title: _t("Password ?"),
        //     startingValue: null,
        //     feedback: (buffer) => {
        //         console.log("feedback",buffer);
        //     },
        //     getPayload: async (inputPin) => {
        //         if (!inputPin) {
        //             if (self.pos.is_timer_screen) {
        //                 self.pos.is_not_remove_screen = false;
        //                 self._showBlurScreen();
        //             }
        //             return false;
        //         }

        //         if (employee.pin === Sha1.hash(inputPin)) {
        //             self.pos.set_cashier(employee);
        //             self.pos.is_timer_screen = false;
        //             self.pos.is_not_remove_screen = true;
        //             self._removeBlurScreen();
        //             return employee;
        //         } else {
        //             alert("Incorrect Password");
        //             if (self.pos.is_timer_screen) {
        //                 self.pos.is_not_remove_screen = false;
        //                 self._showBlurScreen();
        //             }
        //             return false;
        //         }
        //     },
        // });
        if (!inputPin) {
            if (self.pos.is_timer_screen) {
                self.pos.is_not_remove_screen = true;
                self._showBlurScreen();
            }
            return false;
        }
        console.log("validacion...............")
        
        const allEmployees = this.pos.models["hr.employee"].filter(
            (emp) => emp.id 
        );
        const pinMatchEmployees = allEmployees.filter(
            (emp) => !inputPin || Sha1.hash(inputPin) === emp._pin
        );
        
        if ((!pinMatchEmployees.length && !inputPin) || (inputPin && !pinMatchEmployees.length)){
            alert("Incorrect Password");
            if (self.pos.is_timer_screen) {
                self.pos.is_not_remove_screen = false;
                self._showBlurScreen();
            }
            return false;
        }
        else if(pinMatchEmployees.length > 1){
            alert("Employees have same password");
            if (self.pos.is_timer_screen) {
                self.pos.is_not_remove_screen = false;
                self._showBlurScreen();
            }
            return false;
        }
        else if (pinMatchEmployees.length === 1) {
            let emp = pinMatchEmployees[0];
            self.pos.set_cashier(emp);
            self.pos.is_timer_screen = false;
            self.pos.is_not_remove_screen = true;
            self._removeBlurScreen();
            return emp;
        } else {
            alert("Incorrect Password");
            if (self.pos.is_timer_screen) {
                self.pos.is_not_remove_screen = false;
                self._showBlurScreen();
            }
            return false;
        }

        
    },

    _showBlurScreen() {
        const posElement = document.querySelector(".pos");
        if (posElement) {
            const blurScreen = document.createElement("div");
            blurScreen.className = "blur_screen";
            blurScreen.innerHTML = "<h3>Tap to unlock...</h3>";
            posElement.parentNode.insertBefore(blurScreen, posElement);
        }
    },

    _removeBlurScreen() {
        document.querySelectorAll(".blur_screen").forEach((el) => el.remove());
    },

    async sh_start() {
        const self = this;
        if (this.pos.config.sh_enable_auto_lock) {
            let start_timer;
            let elapsed_time = 0;
            let last_time = Date.now();

            const set_logout_interval = function () {
                elapsed_time = 0;
                const logout_interval = function () {
                    const current_time = Date.now();
                    const delta_time = current_time - last_time;
                    last_time = current_time;
                    elapsed_time += delta_time;

                    if (elapsed_time >= self.pos.config.sh_lock_timer * 1000) {
                        self.pos.is_timer_screen = true;
                        self._showBlurScreen();
                    } else {
                        start_timer = requestAnimationFrame(logout_interval);
                    }
                };
                start_timer = requestAnimationFrame(logout_interval);
            };

            const reset_timer = function () {
                if (start_timer) {
                    cancelAnimationFrame(start_timer);
                }
                set_logout_interval();
            };

            if (this.pos.config.sh_lock_timer) {
                document.addEventListener("click", async function (event) {
                    if (self.pos.config.sh_enable_auto_lock && self.pos.config.sh_lock_timer) {
                        reset_timer();

                        if (document.querySelector(".blur_screen")) {
                            if (!self.pos.is_not_remove_screen || event.target.className === 'blur_screen') {
                                self.pos.is_not_remove_screen = true;
                                const cashier = self.pos.get_cashier();
                                // const pin_ok = await self.askPin(cashier);
                                if (!cashier._pin)
                                    return self._removeBlurScreen();
                                // self._removeBlurScreen();
                                return self.askPin(cashier);
                            } 
                            // else {
                            //     self.pos.is_not_remove_screen = false;
                            // }

                            // // Si tienes habilitado el módulo de RRHH, permitir cambiar de cajero después de desbloquear
                            // if (self.pos.config.module_pos_hr) {
                            //     if (!Array.isArray(self.pos.employees) || self.pos.employees.length === 0) {
                            //         return self.pos.get_cashier();
                            //     }

                            //     const list = self.pos.employees.map((employee) => ({
                            //         id: employee.id,
                            //         item: employee,
                            //         label: employee.name,
                            //         isSelected: employee.name === self.pos.get_cashier().name,
                            //     }));

                            //     const { confirmed, payload: selectedCashier } = await self.dialog.add(SelectionPopup, {
                            //         title: _t("Change Cashier"),
                            //         list: list,
                            //     });

                            //     if (!confirmed) {
                            //         self.pos.is_not_remove_screen = true;
                            //         event.preventDefault();
                            //         self._showBlurScreen();
                            //         return false;
                            //     }

                            //     if (!selectedCashier.pin) {
                            //         self.pos.set_cashier(selectedCashier);
                            //     } else {
                            //         const pin_valid = await self.askPin(selectedCashier);
                            //         if (pin_valid) {
                            //             self.pos.set_cashier(selectedCashier);
                            //         } else {
                            //             self.pos.is_not_remove_screen = true;
                            //             event.preventDefault();
                            //             self._showBlurScreen();
                            //             return false;
                            //         }
                            //     }
                            // }
                        }
                    }
                });

                set_logout_interval();
            }
        }
    },

});
