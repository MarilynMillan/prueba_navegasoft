import { Order } from "@pos_preparation_display/app/components/order/order";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async clickOrder() {
        if (this.actionInProgress) {
            return;
        }
        try {
            this.actionInProgress = true;
            const order = this.props.order;
            if (order.stageId === this.preparationDisplay.lastStage.id) {
                return;
            } else {
                await this.preparationDisplay.sendStrickedLineToNextStage(this.props.order);
            }
        } catch (error) {
            console.warn(error);
        } finally {
            await new Promise(r => setTimeout(r, 500));
            this.actionInProgress = false;
        }
    }
});
