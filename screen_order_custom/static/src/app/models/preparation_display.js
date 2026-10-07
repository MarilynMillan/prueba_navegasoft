import { PreparationDisplay } from '@pos_preparation_display/app/models/preparation_display';
import { Order } from "@pos_preparation_display/app/models/order";
import { OrderlineCustom } from '@screen_order_custom/app/models/orderline';
import { Product } from "@pos_preparation_display/app/models/product";
import { patch } from "@web/core/utils/patch";

patch(PreparationDisplay.prototype, {
    processOrders() {
        this.stages.forEach((stage) => (stage.orders = []));
        for (const index in this.categories) {
            this.categories[index].orderlines = [];
        }

        this.orders = this.rawData.orders.reduce((orders, order) => {
            if (order.stage_id === null) {
                order.stage_id = this.firstStage.id;
            }

            const orderObj = new Order(order);
            orderObj.orderlines = order.orderlines.map((line) => {
                let blinking = false;
                if (this.noteByLines[line.id] && line.internal_note !== this.noteByLines[line.id]) {
                    blinking = true;
                    this.env.services["mail.sound_effects"].play("bell");
                }

                const orderline = new OrderlineCustom(line, orderObj, blinking);
                const product = new Product([orderline.productId, orderline.productName]);

                this.noteByLines[line.id] = line.internal_note;
                this.products[product.id] = product;
                this.orderlines[orderline.id] = orderline;

                orderline.productCategoryIds.forEach((categoryId) => {
                    this.categories[categoryId]?.orderlines?.push(orderline);
                    this.categories[categoryId]?.productIds?.add(orderline.productId);
                });

                return orderline;
            });

            if (orderObj.orderlines.length > 0) {
                orders[order.id] = orderObj;
            }

            return orders;
        }, {});

        this.filterOrders();
        return this.orders;
    }
});
