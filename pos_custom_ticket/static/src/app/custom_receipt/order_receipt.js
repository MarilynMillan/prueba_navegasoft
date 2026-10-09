/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ReceiptHeader } from "@pos_custom_ticket/app/custom_receipt/header/receipt_header";

const { DateTime } = luxon;

export class Orderline extends Component {
  static template = "pos_custom_ticket.Orderline";
  floatToInt(value) {
    return parseInt(value);
  }
}

export class OrderBody extends Component {
  static template = "pos_custom_ticket.OrderBody";
  static components = { Orderline };
}

export class OrderReceipt extends Component {
  static template = "pos_custom_ticket.OrderReceipt";
  static components = { Orderline, OrderBody, ReceiptHeader };
  static props = {
    data: Object,
    formatCurrency: Function,
    basic_receipt: { type: Boolean, optional: true },
    orderUuid: { type: String, optional: true },
    dianValues: { type: Object, optional: true }
  };
  static defaultProps = { basic_receipt: false };
  setup() {
    super.setup();
    this.pos = usePos();
  }
  get order() {
    return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
  }
  getTableName() {
    const table = this.order.getTable();
    if (table) {
        let floorAndTable = "";

        if (this.pos.models["restaurant.floor"].length > 0) {
            floorAndTable = `${table.floor_id.name}/`;
        }

        floorAndTable += table.getName();
        return floorAndTable;
    }
    return "";
  }
  get orderlines() {
    const tipProduct = this.pos.config.tip_product_id;
    console.log("Data: ", this.props.data);
    console.log("Order: ", this.order);
    let resultLines = this.props.data.orderlines.filter((line) => line.product_id !== tipProduct?.id)
    return resultLines;
  }
  get orderDate() {
    return DateTime.now().toLocaleString();
  }
  get orderTime() {
    return DateTime.now().toLocal().toFormat("hh:mm a");
  }
  get tipLine() {
    const tipProduct = this.pos.config.tip_product_id;
    const line = this.props.data.orderlines.find(
      (line) => line.product_id === tipProduct?.id
    );
    if (line) {
      return {
        productName: tipProduct?.name,
        amount: line.price,
        amount_currency: parseFloat(line.price.split(/\D\s/)[1].replace(".", "").replace(",", "."))
      };
    }
    return undefined;
  }
  parseCustomerAddress(customer) {
    let address = [];
    if (customer.street) address.push(customer.street);
    if (customer.street2) address.push(customer.street2);
    // if (customer.city) address.push(customer.city);
    // if (customer.state_id) address.push(customer.state_id.name);

    return address.join(", ");
  }
  omit(...args) {
    return omit(...args);
  }
  doesAnyOrderlineHaveTaxLabel() {
    return this.props.data.orderlines.some((line) => line.taxGroupLabels);
  }
  splitStr(str) {
    return str.match(/.{1,40}/g);
  }
}
