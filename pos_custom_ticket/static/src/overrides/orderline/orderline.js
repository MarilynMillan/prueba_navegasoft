/** @odoo-module **/

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

const lineShape = Orderline.props?.line?.shape || {};
Orderline.props = {
  ...Orderline.props,
  line: {
    ...Orderline.props.line,
    shape: {
      ...lineShape,
      product_id: { type: Number, optional: true },
    },
  },
};
