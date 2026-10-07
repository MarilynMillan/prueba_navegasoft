/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { SplitBillScreen } from "@pos_restaurant/app/split_bill_screen/split_bill_screen";
import { patch } from "@web/core/utils/patch";

// ================================================================
// FIX 1: MERGE — Evitar cancelación fantasma al fusionar mesas
// ================================================================
patch(PosStore.prototype, {
    async transferOrder(orderUuid, destinationTable) {
        const order = this.models["pos.order"].getBy("uuid", orderUuid);
        const destinationOrder = this.getActiveOrdersOnTable(destinationTable)[0];

        if (!destinationOrder) {
            return await super.transferOrder(orderUuid, destinationTable);
        }

        const sourceOrderId = typeof order.id === "number" ? order.id : null;
        const destOrderId =
            typeof destinationOrder.id === "number" ? destinationOrder.id : null;

        const sourcePrepByProduct = {};
        for (const [key, prepLine] of Object.entries(
            order.last_order_preparation_change.lines || {}
        )) {
            const productKey =
                prepLine.product_id + "_" + (prepLine.note || "").trim();
            sourcePrepByProduct[productKey] = { ...prepLine };
        }

        order.last_order_preparation_change.lines = {};

        await super.transferOrder(orderUuid, destinationTable);

        if (destinationOrder.last_order_preparation_change) {
            for (const line of destinationOrder.lines) {
                const lineKey = line.preparationKey;
                if (destinationOrder.last_order_preparation_change.lines[lineKey]) {
                    continue;
                }
                const productKey =
                    line.product_id.id + "_" + (line.note || "").trim();
                const sourcePrepLine = sourcePrepByProduct[productKey];
                if (sourcePrepLine) {
                    destinationOrder.last_order_preparation_change.lines[lineKey] = {
                        uuid: line.uuid,
                        product_id: sourcePrepLine.product_id,
                        name: sourcePrepLine.name,
                        basic_name: sourcePrepLine.basic_name,
                        display_name: sourcePrepLine.display_name,
                        note: sourcePrepLine.note || "",
                        quantity: line.qty,
                        attribute_value_ids: sourcePrepLine.attribute_value_ids || [],
                        isCombo: sourcePrepLine.isCombo || false,
                    };
                    line.setHasChange(false);
                    line.saved_quantity = line.qty;
                    delete sourcePrepByProduct[productKey];
                }
            }
            await this.syncAllOrders({ orders: [destinationOrder] });
        }

        if (sourceOrderId && destOrderId) {
            try {
                await this.data.call(
                    "pos_preparation_display.order",
                    "reassign_preparation_orders",
                    [sourceOrderId, destOrderId]
                );
            } catch (e) {
                console.warn("fix_pos_merge_kitchen: Error reasignando pdis_orders", e);
            }
        }
    },
});

// ================================================================
// FIX 2: SPLIT — Crear pdis_lines silenciosamente para la orden
// dividida y ajustar la original sin marcar como cancelado
// ================================================================
patch(SplitBillScreen.prototype, {
    async postSplitOrder(originalOrder, newOrder) {
        await super.postSplitOrder(originalOrder, newOrder);

        const newOrderId = typeof newOrder.id === "number" ? newOrder.id : null;
        const originalOrderId =
            typeof originalOrder.id === "number" ? originalOrder.id : null;

        if (!newOrderId || !originalOrderId) {
            return;
        }

        const splitLines = [];
        for (const line of newOrder.lines) {
            const prepLine =
                newOrder.last_order_preparation_change.lines[line.preparationKey];
            if (prepLine && prepLine.quantity > 0) {
                splitLines.push({
                    product_id: line.product_id.id,
                    qty: prepLine.quantity,
                    note: prepLine.note || "",
                    uuid: line.uuid,
                    attribute_value_ids: line.attribute_value_ids
                        ? line.attribute_value_ids.map((a) => a.id)
                        : [],
                });
            }
        }

        if (splitLines.length > 0) {
            try {
                await this.pos.data.call(
                    "pos_preparation_display.order",
                    "create_split_preparation_order",
                    [newOrderId, originalOrderId, splitLines]
                );
            } catch (e) {
                console.warn("fix_pos_merge_kitchen: Error creando pdis para split", e);
            }
        }
    },
});
