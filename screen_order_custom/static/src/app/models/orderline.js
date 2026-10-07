import { Reactive } from "@web/core/utils/reactive";

export class OrderlineCustom extends Reactive {
    constructor(args, order, blinkingNote) {
        super();
        this.setup(...arguments);
    }

    async setup(args, order, blinkingNote) {
        this.id = args.id;
        this.internalNote = args.internal_note;
        this.productCancelled = args.product_cancelled;
        this.productCategoryIds = args.product_category_ids;
        this.productId = args.product_id;
        this.productName = args.product_name;
        this.productQuantity = args.product_quantity;
        this.attribute_ids = args.attribute_ids ?? [];
        this.todo = args.todo;
        this.order = order;
        this.blinkingNote = blinkingNote || false;
        this.pos_combo_list = false;

        try {
            this.pos_combo_list = JSON.parse(args.pos_combo_list) || false;
        } catch (e) {
            this.pos_combo_list = false;
        }

        if (this.blinkingNote) {
            setTimeout(() => {
                this.blinkingNote = false;
            }, 20000);
        }
    }

    get isCancelled() {
        return this.productCount === 0 ? true : false;
    }

    get productCount() {
        const productCount = this.productQuantity - this.productCancelled;
        return productCount;
    }
}
