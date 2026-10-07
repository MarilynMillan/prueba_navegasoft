/*@odoo-module*/

/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ComboPopupWidget } from "@pos_combo_products/overrides/popup/popup";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";
import { formatFloat, roundDecimals, roundPrecision, floatIsZero, } from "@web/core/utils/numbers";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { Chrome } from "@point_of_sale/app/pos_app";
import { useService } from "@web/core/utils/hooks";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },
});

patch(OrderSummary.prototype, {
    clickLine(ev, orderline) {
        if (orderline.isSelected()) {
            return;
        } else {
            super.clickLine(ev, orderline);
        }
    },
});

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        this._loadPosComboGroups(this.data.models["combo.groups"].getAll());
        this._loadPosComboProducts(this.data.models["combo.products"].getAll());
    },
    _loadPosComboGroups: function (combo_groups) {
        if (combo_groups) {
            var self = this;
            self.all_combo_groups = combo_groups;
            self.all_combo_groups_by_id = {};
            combo_groups.forEach(function (combo_group) {
                self.all_combo_groups_by_id[combo_group.id] = combo_group;
            });
        }
    },
    _loadPosComboProducts: function (combo_products) {
        if (combo_products) {
            var self = this;
            self.all_combo_products = combo_products;
            self.all_combo_products_by_id = {};
            combo_products.forEach(function (combo_product) {
                self.all_combo_products_by_id[combo_product.id] = combo_product;
            });
        }
    },
    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        var product = vals.product_id;
        var self = this;
        if (product.is_combo_product) {
            if (product.pos_combo_groups_ids && !product.product_variant_ids) {
                self.dialog.add(ComboPopupWidget, {
                    title: product.display_name,
                    groups: product.pos_combo_groups_ids,
                    product: product,
                });
                return super.addLineToCurrentOrder(...arguments);
            }
        }
        else {
            return super.addLineToCurrentOrder(...arguments);
        }
    },

});

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.qty_combo_dict = this.qty_combo_dict || {};
    },
});

patch(PosOrderline.prototype, {
    grid_get_combo_product() {
        var grid_temp_arr = []
        var self = this;
        var wk_val = 0;
        for (var key of Object.keys(self.grid_template_dict)) {
            grid_temp_arr.push(self.grid_template_dict[key])
        }
        for (var key of Object.keys(this.sel_combo_prod)) {
            if (this.sel_combo_prod[key]['manage_inventory'] == true && grid_temp_arr.length) {
                this.sel_combo_prod[key]["combo_qty"] = parseInt(grid_temp_arr[wk_val]);
            }
            else {
                this.sel_combo_prod[key]["combo_qty"] = 1;
            }
            wk_val += 1
        };
        return grid_temp_arr;
    },

    get_combo_product() {
        var temp_arr = []
        var self = this;
        var wk_val = 0;
        for (var key of Object.keys(self.template_dict)) {
            temp_arr.push(self.template_dict[key])
        }
        for (var key of Object.keys(this.sel_combo_prod)) {
            if (this.sel_combo_prod[key]['manage_inventory'] == true && temp_arr.length) {
                this.sel_combo_prod[key]["combo_qty"] = parseInt(temp_arr[wk_val]);
            }
            else {
                this.sel_combo_prod[key]["combo_qty"] = 1;
            }
            wk_val += 1
        };
        return temp_arr;
    },

    getDisplayData() {
        const result = super.getDisplayData()
        if(typeof(this.sel_combo_prod) === 'string'){
            this.sel_combo_prod = JSON.parse(this.sel_combo_prod);
            this.grid_temp_arr = JSON.parse(this.grid_temp_arr);
        }
        result["orderline_id"] = this.id;
        return result;
    },

    can_be_merged_with(orderline) {
        const productPriceUnit = this.models["decimal.precision"].find((dp) => dp.name === "Product Price").digits;
        const PriceUnit = this.models["decimal.precision"].find((dp) => dp.name === "Payment Terms").digits;
        const price = window.parseFloat(roundDecimals(this.price_unit || 0, productPriceUnit).toFixed(productPriceUnit));
        let order_line_price = orderline.get_product().get_price(orderline.order_id.pricelist_id, this.get_quantity());
        order_line_price = roundDecimals(order_line_price, PriceUnit);

        if (this.get_product().id !== orderline.get_product().id) { 
            return false;
        }
        else if (this.is_combo_product) {
            return false;
        }
        else if (!this.get_unit() || !this.get_unit().is_pos_groupable) {
            return false;
        } else if (this.get_discount() > 0) { 
            return false;
        } else if (!floatIsZero(price - order_line_price - orderline.get_price_extra(), PriceUnit)) {
            return false;
        } else if (this.product_id.tracking == 'lot' && (this.pos.picking_type.use_create_lots || this.pos.picking_type.use_existing_lots)) {
            return false;
        } else if (this.description !== orderline.description) {
            return false;
        } else if (orderline.get_customer_note() !== this.get_customer_note()) {
            return false;
        } else if (this.refunded_orderline_id) {
            return false;
        } else {
            return true;
        }
    },

    set_unit_price(price) {
        if(price){
            super.set_unit_price(price);
        }else{
            return;
        }
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                orderline: { type: Object, optional: true },
            },
        },
    },
});
