/** @odoo-module */
/* global Sha1 */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ControlButtons.prototype, {

    /**
     * Cambiar Mesero - v2 con PIN obligatorio y auditoría en chatter
     *
     * Flujo:
     * 1. Verifica que haya orden activa
     * 2. Verifica permisos de manager
     * 3. Muestra lista de empleados para seleccionar nuevo mesero
     * 4. Pide PIN del manager con bullets (•) - mismo patrón que pos_hr nativo
     * 5. Valida PIN con SHA1 hash contra employee._pin
     * 6. Aplica el cambio
     * 7. Registra en chatter vía RPC fire-and-forget (no bloquea el POS)
     */
    async clickChangeWaiter() {
        const currentOrder = this.pos.get_order();

        if (!currentOrder) {
            this.notification.add(_t("No hay una orden activa."), { type: "warning" });
            return;
        }

        // --- 1. Verificar permisos: solo rol "manager" ---
        const cashier = this.pos.get_cashier();
        if (!cashier || cashier._role !== "manager") {
            this.notification.add(
                _t("Acceso denegado. Solo usuarios con permisos avanzados pueden cambiar el mesero."),
                { type: "danger" }
            );
            return;
        }

        // --- 2. Construir lista de empleados ---
        const employeeList = [];
        const employees = this.pos.models["hr.employee"]
            ? this.pos.models["hr.employee"].getAll()
            : [];

        for (const employee of employees) {
            if (employee.name) {
                employeeList.push({
                    id: employee.id,
                    label: employee.name,
                    isSelected: currentOrder.waiter_name === employee.name,
                    item: employee,
                });
            }
        }

        // Fallback a res.users si no hay empleados HR cargados
        if (!employeeList.length) {
            const users = this.pos.models["res.users"]
                ? this.pos.models["res.users"].getAll()
                : [];
            for (const user of users) {
                if (user.name) {
                    employeeList.push({
                        id: user.id,
                        label: user.name,
                        isSelected: currentOrder.waiter_name === user.name,
                        item: user,
                    });
                }
            }
        }

        if (!employeeList.length) {
            this.notification.add(
                _t("No hay empleados disponibles para asignar como mesero."),
                { type: "warning" }
            );
            return;
        }

        // Ordenar alfabéticamente
        employeeList.sort((a, b) => a.label.localeCompare(b.label));

        // --- 3. Popup selección de nuevo mesero ---
        const selectedEmployee = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Seleccionar Nuevo Mesero"),
            list: employeeList,
        });

        if (!selectedEmployee) {
            return; // Canceló
        }

        // Evitar cambio al mismo mesero
        if (currentOrder.waiter_name === selectedEmployee.name) {
            this.notification.add(
                _t("El mesero seleccionado ya es el asignado a esta orden."),
                { type: "info" }
            );
            return;
        }

        // --- 4. Pedir PIN del manager (cashier actual) ---
        // Usa el mismo patrón que pos_hr/select_cashier_mixin.js:
        // - formatDisplayedValue reemplaza cada dígito por bullet (•)
        // - Valida contra _pin que es SHA1 hash del PIN configurado en HR
        if (!cashier._pin) {
            this.notification.add(
                _t("El empleado %s no tiene PIN configurado. Configúrelo en Empleados > Ajustes HR.", cashier.name),
                { type: "danger" }
            );
            return;
        }

        const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
            formatDisplayedValue: (x) => x.replace(/./g, "•"),
            title: _t("Ingrese su PIN para autorizar"),
        });

        if (!inputPin) {
            return; // Canceló
        }

        // --- 5. Validar PIN con SHA1 (igual que el nativo) ---
        if (cashier._pin !== Sha1.hash(inputPin)) {
            this.notification.add(
                _t("PIN incorrecto. Cambio de mesero cancelado."),
                { type: "warning" }
            );
            return;
        }

        // --- 6. Aplicar el cambio ---
        const previousWaiter = currentOrder.waiter_name || _t("(sin asignar)");
        currentOrder.waiter_name = selectedEmployee.name;

        // Notificación de éxito
        this.notification.add(
            _t("Mesero cambiado: %s → %s", previousWaiter, selectedEmployee.name),
            { type: "success" }
        );

        // --- 7. Registrar en chatter vía RPC (fire-and-forget, NO bloquea) ---
        const orderUuid = currentOrder.uuid || "";
        if (orderUuid) {
            this.pos.data.call(
                "pos.order",
                "log_waiter_change",
                [orderUuid, previousWaiter, selectedEmployee.name, cashier.name]
            ).catch(() => {});
        }

        // Cerrar diálogo de Actions si está abierto
        if (this.props.close) {
            this.props.close();
        }
    },

    /**
     * Verifica si el cajero actual tiene permisos de manager
     */
    get isManager() {
        const cashier = this.pos.get_cashier();
        return cashier && cashier._role === "manager";
    },

    /**
     * Retorna el nombre del mesero actual de la orden activa
     */
    get currentWaiterName() {
        const order = this.pos.get_order();
        return order && order.waiter_name ? order.waiter_name : "";
    },
});
