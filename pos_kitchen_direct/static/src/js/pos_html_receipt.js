/* @odoo-module */

import { BasePrinter } from "@point_of_sale/app/printer/base_printer";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { toCanvas } from "@point_of_sale/app/utils/html-to-image";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
const { DateTime } = luxon;

const applyWhenMounted = async ({ el, container, callback }) => {
    const elClone = el.cloneNode(true);
    const sameClassElements = container.querySelectorAll(`.${[...el.classList].join(".")}`);
    sameClassElements.forEach(element => element.remove());
    container.appendChild(elClone);
    const res = await callback(elClone);
    return res;
};

const htmlToCanvas = async (el, options) => {
    el.classList.add(options.addClass || "");
    const container = document.querySelector(".render-container");
    if (!container) {
        console.error("render-container no encontrado");
        return;
    }
    return await applyWhenMounted({
        el,
        container: container,
        callback: async (el) => {
            return toCanvas(el, {
                backgroundColor: "#ffffff",
                height: Math.ceil(el.clientHeight),
                width: Math.ceil(el.clientWidth),
                pixelRatio: 3,
            });
        },
    });
};

patch(BasePrinter.prototype, {
    async printReceipt(receipt) {
        if (!receipt) return;
        this.receiptQueue.push(receipt);
        let printResult;
        while (this.receiptQueue.length > 0) {
            receipt = this.receiptQueue.shift();
            const canvas = await htmlToCanvas(receipt, { addClass: "pos-receipt-print" });
            if (!canvas) return this.getActionError();
            const image = this.processCanvas(canvas);
            const newReceipt = this.config ? { data: receipt.outerHTML, isBase64: false } : { data: image, isBase64: true };
            try {
                printResult = await this.sendPrintingJob(newReceipt);
            } catch (error) {
                console.error("Error sending printing job:", error);
                return this.getActionError();
            }
            if (!printResult || printResult.result === false) {
                console.error("Printing job failed:", printResult);
                return this.getResultsError(printResult);
            }
        }
        return true;
    },
});

function getStructuredLines(orderLines, referenceOrderLines = [], isNewOrder = false) {
    const structured = [];

    for (const line of orderLines) {
        if (line.combo_parent_id) continue;

        const isComboParent = line.combo_line_ids?.length > 0;
        const isNormal = !isComboParent;

        structured.push({
            type: isComboParent ? 'parent' : 'normal',
            uuid: line.uuid,
            qty: line.qty,
            name: line.name || line.full_product_name || line.display_name || '',
            note: line.note,
            attribute_value_ids: line.attribute_value_ids || [],
            display_name: line.display_name || line.full_product_name || line.name || '',
            children: (line.combo_line_ids || []).map(child => ({
                type: 'child',
                uuid: child.uuid,
                qty: child.qty,
                name: child.name || child.full_product_name || '',
            }))
        });
    }

    if (referenceOrderLines.length) {
        const orderUuids = referenceOrderLines.filter(l => !l.combo_parent_id).map(l => l.uuid);
        structured.sort((a, b) => orderUuids.indexOf(a.uuid) - orderUuids.indexOf(b.uuid));
    }

    return structured;
}

function getOperationalTitle(order, changedlines, title, isNewOrder = false) {
    if (title === 'Cancelled' || title === 'Cancel') return "Productos cancelados";
    if (isNewOrder) return "Nueva orden";

    let hasAdditions = false, hasModifications = false, hasCancellations = false;

    for (const line of changedlines) {
        if (line.qty === 0) hasCancellations = true;
        else {
            const prevLine = order.last_order_preparation_change?.lines?.[line.uuid];
            if (!prevLine) hasAdditions = true;
            else if (line.qty !== prevLine.quantity || line.note !== prevLine.note) hasModifications = true;
        }
    }

    if (hasAdditions && !hasModifications && !hasCancellations) return "Producto agregado";
    if (!hasAdditions && hasCancellations && !hasModifications) return "Producto cancelado";
    if (hasModifications && !hasAdditions && !hasCancellations) return "Cantidad o nota modificada";
    return "Orden modificada";
}

patch(PosStore.prototype, {
    async getRenderedReceipt(order, title, lines, fullReceipt = false, diningModeUpdate) {
        const d = new Date();
        const date_print = `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
        const time = { hours: String(d.getHours()).padStart(2, '0'), minutes: String(d.getMinutes()).padStart(2, '0') };

        const isNewOrder = !order.last_order_preparation_change || !order.last_order_preparation_change.lines;
        const fallbackPrevious = isNewOrder ? {} : order.last_order_preparation_change.lines;

        const relevantLines = [];
        const addedUUIDs = new Set();

        for (const line of lines) {
            const uuid = line.uuid;
            const prev = fallbackPrevious[uuid];
            const prevQty = prev?.qty || prev?.quantity || 0;
            const actualQty = line.qty || line.quantity || 0;
            const resultingQty = actualQty !== 0 ? actualQty : prevQty;
            const current = order.lines.find(l => l.uuid === uuid) || prev;
            if (current && !addedUUIDs.has(uuid)) {
                const updatedLine = { ...current };
                updatedLine.qty = resultingQty;
                updatedLine.name = current.name || current.full_product_name || current.display_name || '';
                updatedLine.display_name = updatedLine.name;
                relevantLines.push(updatedLine);
                addedUUIDs.add(uuid);

                for (const child of (current.combo_line_ids || [])) {
                    if (!addedUUIDs.has(child.uuid)) {
                        const updatedChild = { ...child };
                        updatedChild.name = child.name || child.full_product_name;
                        const lineChild = lines.find(l => l.uuid === child.uuid);
                        if (lineChild) updatedChild.qty = lineChild.qty || lineChild.quantity;
                        relevantLines.push(updatedChild);
                        addedUUIDs.add(child.uuid);
                    }
                }
            }
        }

        if (relevantLines.length === 0 && Object.keys(fallbackPrevious).length > 0) {
            for (const uuid in fallbackPrevious) {
                const prev = fallbackPrevious[uuid];
                if (!addedUUIDs.has(uuid)) {
                    const lineQty = prev.qty || prev.quantity || 0;
                    const cancelledLine = {
                        uuid: prev.uuid,
                        qty: lineQty,
                        name: prev.name || prev.full_product_name || prev.display_name || '',
                        display_name: prev.display_name || prev.full_product_name || prev.name || '',
                        note: prev.note || '',
                        combo_line_ids: prev.combo_line_ids || [],
                        attribute_value_ids: prev.attribute_value_ids || [],
                        type: 'normal',
                    };
                    relevantLines.push(cancelledLine);
                    addedUUIDs.add(uuid);
                    for (const child of (prev.combo_line_ids || [])) {
                        if (!addedUUIDs.has(child.uuid)) {
                            relevantLines.push({
                                ...child,
                                qty: child.qty || child.quantity || 0,
                                name: child.name || child.full_product_name || '',
                                display_name: child.display_name || child.full_product_name || child.name || '',
                            });
                            addedUUIDs.add(child.uuid);
                        }
                    }
                }
            }
        }

        const structuredLines = getStructuredLines(relevantLines, order.lines, isNewOrder);
        const operational_title = getOperationalTitle(order, structuredLines, title, isNewOrder);

        const printingChanges = {
            table_name: order.table_id?.table_number || "",
            config_name: order.config?.name,
            time,
            tracking_number: order.tracking_number,
            takeaway: order.config?.takeaway && order.takeaway,
            employee_name: order.employee_id?.name || order.user_id?.name,
            order_note: order.general_note,
            diningModeUpdate,
            floor_name: order.table_id?.floor_id?.name,
            table_number: order.table_id?.table_number,
            table_seats: order.table_id?.seats,
            user_name: order.user_id?.name,
            name: order.pos_reference || "unknown order",
            lines: structuredLines,
            date_print,
        };

        const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
            operational_title,
            changes: printingChanges,
            changedlines: structuredLines,
            fullReceipt,
        });
        console.log("Receipt rendered:", receipt);
        return receipt;
    }
});
