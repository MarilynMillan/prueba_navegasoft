/** @odoo-module */

import { Order } from "@pos_preparation_display/app/components/order/order";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    _isKitchenDisplay() {
        const displayType = this.preparationDisplay.rawData?.display_type;
        return displayType === 'kitchen' || !displayType;
    },

    async clickOrder() {
        if (this.actionInProgress) {
            return;
        }

        const order = this.props.order;

        if (order.stageId === this.preparationDisplay.lastStage.id) {
            return;
        }

        if (this._isKitchenDisplay() && this._willReachLastStage(order)) {
            const orderInfo = this._getOrderDescription(order);
            return new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: "Confirmar envío",
                    body: `¿Enviar ${orderInfo} para Listo?`,
                    confirmLabel: "Sí, enviar",
                    cancelLabel: "Cancelar",
                    confirm: async () => {
                        await this._executeClickOrder();
                        resolve();
                    },
                    cancel: () => {
                        resolve();
                    },
                });
            });
        }

        await this._executeClickOrder();
    },

    async _executeClickOrder() {
        if (this.actionInProgress) {
            return;
        }
        try {
            this.actionInProgress = true;
            const order = this.props.order;
            if (order.stageId === this.preparationDisplay.lastStage.id) {
                return;
            }
            await this.preparationDisplay.sendStrickedLineToNextStage(this.props.order);
        } catch (error) {
            console.warn(error);
        } finally {
            await new Promise((r) => setTimeout(r, 500));
            this.actionInProgress = false;
        }
    },

    async resetOrder() {
        const order = this.props.order;

        if (this._isKitchenDisplay()) {
            const orderInfo = this._getOrderDescription(order);
            return new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: "Confirmar restablecimiento",
                    body: `¿Restablecer ${orderInfo} a Por Preparar?`,
                    confirmLabel: "Sí, restablecer",
                    cancelLabel: "Cancelar",
                    confirm: async () => {
                        await this.preparationDisplay.changeOrderStage(order, true);
                        resolve();
                    },
                    cancel: () => {
                        resolve();
                    },
                });
            });
        }

        await this.preparationDisplay.changeOrderStage(order, true);
    },

    _willReachLastStage(order) {
        const stages = [...this.preparationDisplay.stages.values()];
        const currentStageIdx = stages.findIndex((s) => s.id === order.stageId);

        if (currentStageIdx === -1) {
            return false;
        }

        const nextStage = stages[currentStageIdx + 1];
        if (!nextStage) {
            return false;
        }

        return nextStage.id === this.preparationDisplay.lastStage.id;
    },

    _getOrderDescription(order) {
        const parts = [];

        if (order.table && order.table.table_number) {
            parts.push(`Mesa ${order.table.table_number}`);
        }

        if (order.waiter_name) {
            parts.push(order.waiter_name);
        }

        return parts.length > 0 ? parts.join(" - ") : "esta orden";
    },
});
