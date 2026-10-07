import { Component } from "@odoo/owl";

export class ReceiptHeader extends Component {
  static template = "pos_custom_ticket.ReceiptHeader";
  static props = {
    data: {
      type: Object,
      shape: {
        company: Object,
        "*": true,
      },
    },
  };
  get companyAddress() {
    const { company } = this.props.data;
    let address = [];

    if (company.street) address.push(company.street);
    if (company.street2) address.push(company.street2);
    if (company.city) address.push(company.city);
    if (company.state_id) address.push(company.state_id.name);

    return address.join(", ");
  }
}
