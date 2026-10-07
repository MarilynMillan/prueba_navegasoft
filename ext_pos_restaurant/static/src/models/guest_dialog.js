import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class GuestDialog extends NumberPopup {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    }
    _validateBuffer() {
        if (this.state.buffer == '' || this.state.buffer < 1) {
            this.dialog.add(AlertDialog, {
                title: _t("Error de validación"),
                body: _t("Elija un número de comensales antes de continuar"),
            });
            return false;
        }
        return true;
    }
    onEscape() {
        if (!this._validateBuffer()) return;
        super.onEscape(...arguments);
    }
    confirm() {
        if (!this._validateBuffer()) return;
        super.confirm(...arguments);
    }
    close() {
        if (!this._validateBuffer()) return;
        super.close(...arguments);
    }
}

export function add(self, order) {
    self.dialog.add(GuestDialog, {
        startingValue: order?.getCustomerCount() || 0,
        title: _t("Guests?"),
        feedback: (buffer) => {
            const value = self.env.utils.formatCurrency(
                order?.amountPerGuest(parseInt(buffer, 10) || 0) || 0
            );
            return value ? `${value} / ${_t("Guest")}` : "";
        },
        getPayload: (inputNumber) => {
            const guestCount = parseInt(inputNumber, 10) || 0;
            if (guestCount == 0 && order.lines.length === 0) {
                self.removeOrder(order);
                self.showScreen("FloorScreen");
                return;
            }
            order.setCustomerCount(guestCount);
            if (order.customer_count > 0) {
                order.initial_customer_count = true;
            }
            self.addPendingOrder([order.id]);
        }
    }, {
        onClose() {
            if (order.customer_count == '' || order.customer_count < 1) {
                add(self, order);
            }
        }
    });
}