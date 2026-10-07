/*@odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ComboPopupWidget } from "@pos_combo_products/overrides/popup/popup";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(OrderSummary.prototype, {
    _setValue(val) {
        var self = this;
        var curr_orderline = self.currentOrder.get_selected_orderline()
        if (curr_orderline === undefined) {
            super._setValue(val)
        } else {
            var combo_line = self.currentOrder.get_selected_orderline().product_id.is_combo_product;
            if (curr_orderline) {
                if (self.env.services.pos.numpadMode === 'quantity') {
                    if (!combo_line) {
                        super._setValue(val)
                    } else {
                        if (val != 'remove') {
                            curr_orderline.input_quantity = val
                            curr_orderline.set_quantity(val)
                            curr_orderline.price_type = "manual";
                            curr_orderline.set_unit_price(curr_orderline.price);
                        } else {
                            self.currentOrder.removeOrderline(curr_orderline)
                        }
                    }
                } else if (self.env.services.pos.numpadMode === 'price') {
                    if (!combo_line) {
                        super._setValue(val);
                    } else {
                        self.env.services.dialog.add(AlertDialog, {
                            title: this.env._t('Not Allowed'),
                            body: this.env._t("You cannot change price of a Combo Product."),
                        });
                    }
                } else {
                    super._setValue(val)
                }
            } else {
                super._setValue(val)
            }
        }
    }
});

patch(ProductCard.prototype, {
    wk_is_combo_product(product_id) {
        var self = this;
        var combo_prod_items = {}
        var len = 0
        self.env.services.pos.models["product.product"].getAll().forEach(product => {
            if (product.is_combo_product == true) {
                combo_prod_items[product.id] = product
                len += 1
            }
        });
        for (var i in combo_prod_items) {
            if (combo_prod_items[i].id == product_id && combo_prod_items[product_id].hide_product_price) {

                return true;
            }
        }
    }
});
patch(Orderline.prototype, {
    open_combo_popup() {
        var self = this;
        var orderline = self.env.services.pos.models['pos.order.line'].get(this.props.line.orderline_id)
        self.env.services.dialog.add(ComboPopupWidget, {
            title: orderline.product_id.display_name,
            groups: orderline.product_id.pos_combo_groups_ids,
            product: orderline.product_id,
            line: orderline,
        });
    }
});
patch(TicketScreen.prototype, {
    cleanJson(data) {
        if (typeof data === 'string') {
            return data
                .replace(/'/g, '"')
                .replace(/\bTrue\b/g, 'true')
                .replace(/\bFalse\b/g, 'false');
        }
        return data;
    }
});

