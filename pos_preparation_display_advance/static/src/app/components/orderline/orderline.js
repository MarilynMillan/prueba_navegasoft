/** @odoo-module */

import { Orderline } from "@pos_preparation_display/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

/**
 * Bloquea el subrayado (strikethrough) de productos que NO pertenecen
 * a las categorías propias (owned_category_ids) de esta pantalla.
 *
 * Ejemplo: En pantalla PIZZA con owned = [PIZZAS E CALZONES],
 * el cocinero NO puede subrayar pastas individualmente.
 * Solo puede enviar la orden completa tocando el header.
 */
patch(Orderline.prototype, {
    async changeOrderlineStatus() {
        const ownedCategoryIds = odoo.preparation_display?.owned_category_ids;

        // Si no hay owned categories configuradas, todo es interactuable
        if (!ownedCategoryIds || ownedCategoryIds.length === 0) {
            return super.changeOrderlineStatus(...arguments);
        }

        // Verificar si el producto pertenece a las categorías propias
        const productCategoryIds = this.props.orderline.productCategoryIds || [];
        const isOwned = productCategoryIds.some(
            (catId) => ownedCategoryIds.includes(catId)
        );

        if (!isOwned) {
            // Producto NO es de esta pantalla → no permitir subrayar
            return;
        }

        return super.changeOrderlineStatus(...arguments);
    },
});
