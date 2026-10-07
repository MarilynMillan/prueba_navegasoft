/*@odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { Component } from "@odoo/owl";
import { onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class MinQtyPopupWidget extends Component {
    static template = "MinQtyPopupWidget";
    static components = { Dialog };
    click_min_comfirm() {
        this.cancel();
    }
    cancel() {
        this.props.close();
    }
}

export class ComboPopupWidget extends Component {
    static template = "ComboPopupWidget";
    static components = { Dialog };
    setup() {
        super.setup();
        onMounted(this.onMounted);
    }

    onMounted() {
        var self = this;
        // remove sign
        $('.remove_sel_prod').click(function (e) {
            var prod_el;
            if (e) {
                if ($(e.target)) {
                    prod_el = $(e.target).parent().parent();
                }
            }
            if (prod_el) {
                e.stopPropagation();
                if (prod_el.hasClass('selected_grid_product')) {
                    prod_el.removeClass('selected_grid_product');
                }
                if (prod_el.find('.grid_qty')) {
                    prod_el.find('.grid_qty').text(0);
                }
            }
        })

        // grid view 
        $('.grid_product').click(function (e) {
            var qty_el = $(e.currentTarget).find('.grid_qty')
            var prod_id = $(e.currentTarget).attr('data-id')
            var line = self.props.line;
            $('.tab-content.current .selected_grid_product').removeClass('last_clicked');
            $(e.currentTarget).addClass('last_clicked')
            var product = self.env.services.pos.all_combo_products_by_id[prod_id];
            if (product.manage_inventory) {
                var qty = qty_el.text();
                qty = parseInt(qty) + 1;
                qty_el.text(qty);
                if (!$(e.currentTarget).hasClass('selected_grid_product')) {
                    $(e.currentTarget).addClass('selected_grid_product');
                }
            } else {
                if ($(e.currentTarget).hasClass('selected_grid_product')) {
                    $(e.currentTarget).removeClass('selected_grid_product');
                    $(e.currentTarget).removeClass('last_clicked')
                } else {
                    $(e.currentTarget).addClass('selected_grid_product');

                }
            }
            $('.tab-content.current').trigger('change');
        })

        // toggle
        $('.switch').click(function (e) {
            var combo_el = $(e.target).next("span");
            if (combo_el.hasClass('combo_check_true')) {
                combo_el.removeClass('combo_check_true');
                $('.tab-content.current .wk_qty_product').removeClass('last_clicked')
                $('.tab-content.current .combo_check').removeClass('last_clicked')
                combo_el.removeClass('last_clicked')
                combo_el.css('color', '#017e84');
                combo_el.text('ADD')
                combo_el.css('background-color', 'rgb(179 228 226)');
                combo_el.removeClass('qty_combo_product');
                $(e.target).prop('checked', false);
                $('.tab-content.current').trigger('change');
            } else {
                combo_el.addClass('combo_check_true');
                combo_el.css('background-color', 'rgb(122 242 131)');
                combo_el.text('REMOVE');
                combo_el.css('color', 'green')
                $(e.target).prop('checked', true);
                combo_el.addClass('qty_combo_product');
                $('.tab-content.current .wk_qty_product').removeClass('last_clicked')
                $('.tab-content.current .combo_check').removeClass('last_clicked')
                combo_el.addClass('last_clicked')
                $('.tab-content.current').trigger('change');
            }
        });

        // list view and grid view from i button with selected options
        var line = self.props.line;
        if (line) {
            var qty_dict = line.order_id.qty_combo_dict
            // list
            if (self.env.services.pos.config.combo_popup_view == 'list') {
                line.sel_combo_prod.forEach(function (product) {
                    if (product.manage_inventory) {
                        if (qty_dict[product.product_id.id]) {
                            $('input.wk_qty_product').each(function (i, el) {
                                if (line.template_dict[$(el).attr('el-id')]) {
                                    $(el).addClass('qty_combo_product');
                                    $('.tab-content.current').trigger('change');
                                    $(el).val(line.template_dict[$(el).attr('el-id')]);
                                }
                            })
                        }
                    } else {
                        $('input.wk_checked_combo').each(function (i, el) {
                            if (line.template_dict[$(el).attr('el-id')]) {
                                $(el).next("span").addClass('qty_combo_product');
                                $('.tab-content.current').trigger('change');
                                $(el).next("span").css('background-color', 'rgb(122 242 131)');
                                $(el).next("span").text('REMOVE');
                                $(el).next("span").css('color', 'green')
                                $(el).next("span").addClass('combo_check_true');
                                $(el).prop('checked', true);
                            }
                        })
                    }
                })
            }
        }

        // minus button
        $('.combo_prod_popup').on('click', '.wk-fa-minus', function (e) {
            var input_element = $(e.target).next();
            var checked_product_id = $(input_element).attr('el-id').substr(0, 4);
            var qty = $(input_element).val()
            qty = parseInt(qty) - 1;
            if ($(input_element)) {
                if (qty < 0) {
                    $(input_element).addClass('text_shake');
                    $(input_element).removeClass('qty_combo_product');
                    $(input_element).css('border-color', 'red')
                    $('.negative_val_error').show()
                    $('.wk_confirm').css('margin-top', '-41px')
                    $('.wk_cancel').css('margin-top', '-41px')
                    setTimeout(function () {
                        $(input_element).css('border-color', '#b0a8a8')
                        $(input_element).removeClass('text_shake');
                        $('.negative_val_error').hide()
                        $('.wk_confirm').css('margin-top', '10px')
                        $('.wk_cancel').css('margin-top', '10px')
                    }, 1500)
                    $('.tab-content.current .wk_qty_product').removeClass('last_clicked')
                    $('.tab-content.current .combo_check').removeClass('last_clicked')
                    $(input_element).removeClass('last_clicked')
                    $('.tab-content.current').trigger('change');
                }
                else if (qty == 0) {
                    $('.tab-content.current .wk_qty_product').removeClass('last_clicked')
                    $('.tab-content.current .combo_check').removeClass('last_clicked')
                    $(input_element).removeClass('qty_combo_product');
                    $(input_element).val(qty)
                    $(input_element).removeClass('last_clicked')
                    $('.tab-content.current').trigger('change');
                } else {
                    $('.tab-content.current .wk_qty_product').removeClass('last_clicked')
                    $('.tab-content.current .combo_check').removeClass('last_clicked')
                    $(input_element).addClass('last_clicked')
                    $(input_element).val(qty)
                    $(input_element).addClass('qty_combo_product');
                    $('.tab-content.current').trigger('change');
                }
            }
        });

        var input_increase = true;
        $('.wk_qty_product').on('input', function (e) {
            $(e.target).addClass('qty_combo_product');
            $(e.target).addClass('last_clicked');
            var tab_groups = $('.tab-content.current');

            var last_selected_option = $('.last_clicked')
            tab_groups.each(function (i, elem) {
                var qty = 0;
                var tab_id = $(elem).attr('id').replace('tab', '')
                var group_data = self.env.services.pos.all_combo_groups_by_id[tab_id];
                var selected_options = $(elem).find('.qty_combo_product');
                selected_options.each(function (i, el) {
                    if ($(el).hasClass('wk_qty_product')) {
                        qty = parseInt(qty) + parseInt($(el).val());
                    } else {
                        qty = parseInt(qty) + 1;
                    }
                });

                if (qty > group_data.maximum_combo_products) {
                    if ($(e.target).val() > 0) {
                        $(e.target).val(0);
                        last_selected_option.next().next().show();
                        setTimeout(function () {
                            last_selected_option.next().next().hide();
                        }, 1500)
                    }
                }
            })
        })

        // for maximum option selection ristriction 
        $('.combo_prod_popup').on('change', '.tab-content.current', function (e) {
            var tab_groups = $('.tab-content.current');
            tab_groups.each(function (i, elem) {
                var qty = 0;
                var tab_id = $(elem).attr('id').replace('tab', '')
                var group_data = self.env.services.pos.all_combo_groups_by_id[tab_id];
                if (self.env.services.pos.config.combo_popup_view == "list") {
                    // var qty = 0;
                    var selected_options = $(elem).find('.qty_combo_product');
                    selected_options.each(function (i, el) {
                        if ($(el).hasClass('wk_qty_product')) {
                            qty = parseInt(qty) + parseInt($(el).val());
                        } else {
                            qty = parseInt(qty) + 1;
                        }
                    });
                    var last_selected_option = $('.last_clicked')
                    input_increase = true;
                    $('.item_count').text(qty + 1);
                    if (qty > group_data.maximum_combo_products) {
                        if (last_selected_option) {
                            if (last_selected_option.hasClass('wk_qty_product')) {
                                input_increase = false;
                                last_selected_option.next().next().show();
                                setTimeout(function () {
                                    last_selected_option.next().next().hide();
                                }, 2000)
                                $('.item_count').text(qty - 1);
                                $('.item_count').text(qty - 1);
                                var lat_sel_qty = last_selected_option.val();
                                last_selected_option.val(lat_sel_qty - 1);
                                last_selected_option.removeClass('qty_combo_product');
                            } else {
                                last_selected_option.parent().next('.max_val_error').show();
                                setTimeout(function () {
                                    last_selected_option.parent().next('.max_val_error').hide();
                                }, 1500)
                                last_selected_option.prev().prop('checked', false);
                                last_selected_option.removeClass('combo_check_true');
                                last_selected_option.removeClass('qty_combo_product');
                                last_selected_option.css('color', '#017e84');
                                last_selected_option.text('ADD')
                                last_selected_option.css('background-color', 'rgb(179 228 226)');
                            }
                        }
                    }
                } else {
                    var grid_selected_options = $(elem).children().eq(1).find('article.selected_grid_product');

                    var qty = 0;
                    grid_selected_options.each(function (i, el) {
                        var wk_element = $(el).find('.grid_qty');
                        if (wk_element.length > 0) {
                            qty = parseInt(qty) + parseInt(wk_element.text());
                        } else {
                            qty = parseInt(qty) + 1;
                        }
                    });
                    var grid_last_selection = $('.last_clicked');
                    if (qty > group_data.maximum_combo_products) {
                        if (grid_last_selection) {
                            grid_last_selection.removeClass('selected_grid_product')
                            grid_last_selection.removeClass('wk_check')
                            grid_last_selection.removeClass('last_clicked')
                            grid_last_selection.addClass('stop_grid_selection')
                            $('.wk_max_val_error').show()
                            var product = self.env.services.pos.all_combo_products_by_id[grid_last_selection.attr('data-id')]
                            if (product) {
                                if (product.manage_inventory) {
                                    var val = grid_last_selection.children().eq(1).text()
                                    grid_last_selection.children().eq(1).text(val - 1)
                                    if ((val - 1) > 0) {
                                        grid_last_selection.addClass('selected_grid_product')
                                    }
                                } else {
                                    grid_last_selection.removeClass('selected_grid_product')
                                }
                            }
                            $('.wk_confirm').css('margin-top', '-41px')
                            $('.wk_cancel').css('margin-top', '-40px')
                            setTimeout(function () {
                                grid_last_selection.removeClass('stop_grid_selection');
                                $('.wk_max_val_error').hide()
                                $('.wk_confirm').css('margin-top', '10px')
                                $('.wk_cancel').css('margin-top', '10px')
                            }, 2000)
                        }
                    }
                }
            })
        });

        // plus button
        $('.fa.wk-fa-plus').click(function (e) {
            var input_element = $(e.target).prev()
            var qty = $(input_element).val()
            qty = parseInt(qty) + 1;
            $(input_element).addClass('qty_combo_product')
            $('.tab-content.current .wk_qty_product').removeClass('last_clicked')
            $('.tab-content.current .combo_check').removeClass('last_clicked')
            $(input_element).addClass('last_clicked');
            if (input_increase) {
                $(input_element).val(qty);
            }
            $('.tab-content.current').trigger('change');
        });
    }

    wk_get_combo_product_image_url(product) {
        return window.location.origin + '/web/image?model=combo.products&field=image&id=' + product.id;
    }

    async wk_click_confirm() {
        var self = this;
        var checked_combos = $('.wk_checked_combo:checked');
        var checked_combo_list = [];
        var qty_combo_list = [];
        var qty_combo_list_name = {};
        var toggle_combo_price = 0;
        var qty_combo_price = 0;
        var template_dict = {};
        var grid_template_dict = {};
        var qty_combo_dict = {};
        var line = self.props.line;
        var combo_products = self.env.services.pos.all_combo_products_by_id;
        var sel_combo_prod = []
        var minimum_qty_dict = {}

        $('.tab-content').each(function (index, el) {
            var tab_id = $(el).attr('id').replace('tab', '');

            var group_data = self.env.services.pos.all_combo_groups_by_id[tab_id];

            if (self.env.services.pos.config.combo_popup_view == "list") {
                var selected_options = $(el).find('.qty_combo_product').length;
                if (selected_options < group_data.minimum_combo_products) {
                    minimum_qty_dict[tab_id] = group_data.minimum_combo_products - selected_options;
                }
            } else {
                var grid_selected_options = $(el).find('.selected_grid_product').length;
                if (grid_selected_options < group_data.minimum_combo_products) {
                    minimum_qty_dict[tab_id] = group_data.minimum_combo_products - grid_selected_options;
                }
            }
        })

        // for the combo has some categories where minimum required qty is not selected 
        if (Object.keys(minimum_qty_dict).length > 0) {
            self.env.services.dialog.add(MinQtyPopupWidget, {
                minimum_qty_dict: minimum_qty_dict,
            });
        } else {
            if (self.env.services.pos.config.combo_popup_view == "list") {

                checked_combos.each(function (idx, element) {
                    var el = combo_products[$(element).data('id')]
                    template_dict[$(element).attr('el-id')] = true;
                    checked_combo_list.push($(element).attr('el-id'))
                    toggle_combo_price = (toggle_combo_price) + el.price;
                    sel_combo_prod.push(el.id)
                })

                $('.wk_qty_product').each(function (idx, element) {
                    var el = combo_products[$(element).data('id')]
                    qty_combo_price = qty_combo_price + (el.price * $(element).val())
                    if ($(element).val() > 0) {
                        if (el.product_id.id in qty_combo_dict) {
                            qty_combo_dict[el.product_id.id] += parseInt($(element).val());
                        } else {
                            qty_combo_dict[el.product_id.id] = parseInt($(element).val());
                        }
                        qty_combo_list_name[el.product_id.id] = el.name
                        qty_combo_list.push(el.product_id);
                        template_dict[$(element).attr('el-id')] = qty_combo_dict[el.product_id.id];
                        sel_combo_prod.push(el.id)
                    }
                })

            } else {
                $('.selected_grid_product').each(function (idx, element) {
                    var el = combo_products[$(element).data('id')]
                    if (el.manage_inventory) {
                        var el_qty = $(element).find('.grid_qty').text()
                        qty_combo_price = (qty_combo_price) + (el.price * el_qty);
                        if (el_qty > 0) {
                            qty_combo_list_name[el.id] = el.name;
                            grid_template_dict[$(element).attr('el-id')] = el_qty;
                            qty_combo_list.push(el.id);
                            qty_combo_dict[el.id] = el_qty;
                            sel_combo_prod.push(el.id)
                        }
                    } else {
                        checked_combo_list.push($(element).data('id'));
                        grid_template_dict[$(element).attr('el-id')] = true;
                        toggle_combo_price = (toggle_combo_price) + el.price;
                        sel_combo_prod.push(el.id)
                    }
                })
            }
            var product = self.env.services.pos.models["product.product"].get(self.props.product.id)
            var order = self.env.services.pos.get_order();
            var total_combo_price;
            if (product) {
                total_combo_price = product.lst_price + qty_combo_price + toggle_combo_price;
            }
            if (self.props.options && self.props.options.price_extra) {
                total_combo_price += self.props.options.price_extra;
            }
            self.props.total_combo_price = total_combo_price;
            var temp_arr = []
            var grid_temp_arr = []
            if (template_dict) {
                for (var key of Object.keys(template_dict)) {
                    temp_arr.push(template_dict[key])
                }
            }
            if (grid_template_dict) {
                for (var key of Object.keys(grid_template_dict)) {
                    grid_temp_arr.push(grid_template_dict[key])
                }
            }
            if (!line) {
                // order.add_product(product, self.props.options)
                var sel_line = order.get_selected_orderline();
                sel_line.set_unit_price(total_combo_price);
                sel_line.price_type = "manual";
                sel_line.sel_combo_prod = sel_combo_prod;
                sel_line.is_combo_product = true;
                sel_line.template_dict = template_dict;
                sel_line.grid_template_dict = grid_template_dict;
                sel_line.qty_combo_dict = qty_combo_dict;
                sel_line.qty_combo_list_name = qty_combo_list_name;
                sel_line.temp_arr = temp_arr;
                sel_line.grid_temp_arr = grid_temp_arr;
            } else {
                line.set_unit_price(total_combo_price);
                line.price_type = "manual";
                line.sel_combo_prod = sel_combo_prod;
                line.grid_template_dict = grid_template_dict;
                line.is_combo_product = true;
                line.template_dict = template_dict;
                line.qty_combo_dict = qty_combo_dict;
                line.qty_combo_list_name = qty_combo_list_name;
                line.temp_arr = temp_arr;
                line.grid_temp_arr = grid_temp_arr;
            }

            for (var qty_key in qty_combo_dict) {
                qty_key = parseInt(qty_key);
                order.qty_combo_dict = {};
                order.qty_combo_dict[qty_key] = qty_combo_dict[qty_key];
            }

            order.qty_wk_combo_ids = order.qty_wk_combo_ids || [].concat(qty_combo_list);
            order.qty_combo_list_name = Object.assign({}, order.qty_combo_list_name, qty_combo_list_name);

            self.confirm();
        }
    }
    confirm() {
        this.props.close();
    }

    cancel() {
        if(this.env.services.pos.get_order().get_selected_orderline().sel_combo_prod && this.env.services.pos.get_order().get_selected_orderline().sel_combo_prod.length){
            this.props.close();
        }else{
            this.env.services.pos.get_order().removeOrderline(this.env.services.pos.get_order().get_selected_orderline());
            this.props.close();
        }
    }
}
