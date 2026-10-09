from werkzeug.routing import ValidationError
from odoo import models, fields
from odoo.tools import float_round

class ChangeEffectiveWizard(models.TransientModel):
    _name = "change.effective.wizard"
    _description = "Change Effective Date"

    def action_update_valuation_layers(self, active_id):
        """
        Custom method to update valuation layers with correct currency conversion rates
        Called after validating a receipt with foreign currency
        """
        for picking in active_id:
            # Your existing code goes here (the entire block you shared)

            # Add code to update product costs after valuation layer changes
            self._update_product_costs_from_valuation(picking)

    def _update_product_costs_from_valuation(self, picking):
        """Update product standard prices based on the new valuation layers"""
        products_to_update = picking.move_ids_without_package.mapped('product_id')

        for product in products_to_update:
            # Get costing method for this product
            costing_method = product.product_tmpl_id.categ_id.property_cost_method

            if costing_method == 'average':
                # For average costing, update the standard price based on all valuation layers
                svls = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', product.id),
                    ('company_id', '=', picking.company_id.id),
                    ('quantity', '>', 0)  # Only consider positive quantities
                ])

                total_qty = 0
                total_value = 0
                for s in svls:
                    if s.remaining_qty > 0:
                        total_qty += s.quantity
                        total_value += s.value

                if total_qty > 0:
                    new_avg_cost = total_value / total_qty

                    # Check if product is a variant (has variants) or not
                    is_variant = len(product.product_tmpl_id.product_variant_ids) > 1

                    if is_variant:
                        # Update the variant's standard price directly
                        product.with_company(picking.company_id.id).write({'standard_price': new_avg_cost})
                    else:
                        # For non-variants, update the template's standard price
                        product.product_tmpl_id.with_company(picking.company_id.id).write({'standard_price': new_avg_cost})

            elif costing_method == 'fifo':
                # For FIFO, we don't update the standard price directly
                # Instead, ensure the most recent receipt's unit cost is reflected correctly

                # Get the most recent valuation layer for this receipt
                recent_svl = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', product.id),
                    ('company_id', '=', picking.company_id.id),
                    ('quantity', '>', 0),  # Only consider positive quantities
                    ('description', 'ilike', str(picking.name + "%"))
                ], order='create_date desc', limit=1)

                if recent_svl:
                    # Check if product is a variant or not
                    is_variant = len(product.product_tmpl_id.product_variant_ids) > 1

                    if is_variant:
                        # For FIFO variants, update the variant's standard price for reference
                        product.with_company(picking.company_id.id).write({
                            'standard_price': recent_svl.unit_cost  # This doesn't affect valuation for FIFO
                        })
                    else:
                        # For non-variants, update the template's standard price
                        product.product_tmpl_id.with_company(picking.company_id.id).write({
                            'standard_price': recent_svl.unit_cost  # This doesn't affect valuation for FIFO
                        })

                    # Make sure related valuation layer has correct unit_cost
                    if recent_svl.unit_cost != recent_svl.value / recent_svl.quantity:
                        corrected_unit_cost = recent_svl.value / recent_svl.quantity
                        recent_svl.unit_cost = corrected_unit_cost
                        recent_svl.remaining_value = recent_svl.remaining_qty * corrected_unit_cost

    # Definisikan field wizard
    effective_date = fields.Datetime(string="Effective Date", help="Date at which the transfer is processed")

    def update_effective_date(self):
        for picking in self.env['stock.picking'].browse(self._context.get('active_ids', [])):

            # Mengatur tanggal done
            selected_date = self.effective_date

            if not selected_date:
                raise ValidationError('Date is not yet selected')

            picking.date_done = selected_date

            # Mengganti tanggal stock.valuation.layer
            self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = (%s) WHERE description LIKE (%s)",
                                [selected_date, str(picking.name + "%")])

            # Mengganti tanggal stock.move.line
            for stock_move_line in self.env['stock.move.line'].search([('reference', 'ilike', str(picking.name + "%"))]):
                stock_move_line.date = selected_date

            # Mengganti tanggal stock.move
            for stock_move in self.env['stock.move'].search([('reference', 'ilike', str(picking.name + "%"))]):
                stock_move.date = selected_date

            # Mengganti tanggal account.move.line
            self.env.cr.execute("UPDATE account_move_line SET date = (%s) WHERE ref SIMILAR TO %s",
                                [selected_date, str(picking.name + "%")])

            # Mengganti tanggal account.move
            self.env.cr.execute("UPDATE account_move set date = (%s) WHERE ref SIMILAR TO %s",
                                [selected_date, str(picking.name + "%")])

            # Mengambil Currency System ID
            system_default_currency = picking.company_id.currency_id.id
            purchase_order = picking.purchase_id

            # Jika PO picking merupakan incoming transfer serta Purchase Order menggunakan currency asing
            # Maka lakukan perhitungan ulang valuasi
            if picking.picking_type_id.code == 'internal':
                pass

            elif picking.picking_type_id.code == 'outgoing':
                if not picking.return_id:
                    journal_entry_ids = []

                    for line in picking.move_ids_without_package:
                        product_id = line.product_id.id
                        valuation_layers = self.env['stock.valuation.layer'].search([
                            ('product_id', '=', product_id),
                            ('reference', 'ilike', str(picking.name + "%"))
                        ])

                        if valuation_layers:
                            for valuation_layer in valuation_layers:
                                account_move = valuation_layer.account_move_id

                                if account_move:
                                    journal_entry_ids.append(account_move.id)

                                    self.env.cr.execute("""
                                        UPDATE account_move
                                        SET name = '/',
                                            state = 'draft',
                                            date = %s,
                                            sequence_prefix = '/',
                                            sequence_number = 0
                                        WHERE id = %s
                                        """, (selected_date, account_move.id))

                                    self.env.cr.commit()

                        line.product_id._run_fifo_vacuum(picking.company_id)

                    # # # Change journal entry name by re-posting it again
                    if journal_entry_ids:
                        for journal_entry_id in journal_entry_ids:
                            account_move = self.env['account.move'].search([('id', '=', journal_entry_id)])

                            year = selected_date.year
                            month = str(selected_date.month).zfill(2)

                            new_sequence_prefix = f"{account_move.journal_id.code}/{year}/{month}/"

                            last_sequence = self.env['account.move'].search([
                                ('sequence_prefix', '=', new_sequence_prefix),
                            ], order='sequence_number desc', limit=1)

                            new_sequence_number = (last_sequence.sequence_number or 0) + 1

                            # Step 1: Set the state to draft using SQL
                            self.env.cr.execute("""
                                            UPDATE account_move
                                            SET state = 'draft'
                                            WHERE id = %s
                                        """, (account_move.id,))

                            # Update the date, name and sequence
                            self.env.cr.execute("""
                                            UPDATE account_move
                                            SET date = %s,
                                                name = %s,
                                                sequence_prefix = %s,
                                                sequence_number = %s
                                            WHERE id = %s
                                        """, (selected_date, f"{new_sequence_prefix}{str(new_sequence_number).zfill(4)}",
                                              new_sequence_prefix, new_sequence_number, account_move.id))

                            # Set back to posted
                            self.env.cr.execute("""
                                        UPDATE account_move
                                        SET state = 'posted',
                                            made_sequence_gap = FALSE
                                        WHERE id = %s
                                    """, (account_move.id,))

                            self.env.cr.commit()

                            # Set the flag to avoid sequence gap warnings
                            self.env.cr.execute("""
                                        UPDATE account_move
                                        SET made_sequence_gap = FALSE
                                        WHERE id = %s
                                    """, (account_move.id,))


            elif picking.picking_type_id.code == 'incoming':
                if not picking.return_id:
                    if picking.picking_type_id.code == 'incoming' and int(purchase_order.currency_id.id) != system_default_currency:

                        stock_move_id = None

                        rate = float_round(picking.purchase_id.currency_id._get_conversion_rate(
                            from_currency=picking.purchase_id.currency_id,
                            to_currency=picking.company_id.currency_id,
                            company=picking.company_id,
                            date=selected_date
                        ), precision_digits=2)

                        duplicate_product = []
                        seen_product_ids = []

                        for product in purchase_order.order_line:
                            product_id = product.product_id.id

                            if product_id in seen_product_ids and product_id not in duplicate_product:
                                duplicate_product.append(product_id)
                            else:
                                seen_product_ids.append(product_id)

                        # Initialize a dictionary to store PO details
                        po_details = {}
                        po_details_duplicate_product = []

                        # Populate PO details
                        for product in purchase_order.order_line:
                            product_id = product.product_id.id
                            if product_id not in po_details and product_id not in duplicate_product:
                                po_details[product_id] = {
                                    'quantity': product.product_qty,
                                    'price_subtotal': product.price_subtotal,
                                }

                            elif product_id in duplicate_product:
                                po_details_duplicate_product.append({
                                    'product_id': product_id,
                                    'quantity': product.product_qty,
                                    'price_subtotal': product.price_subtotal,
                                })

                        # Match PO Detail dengan Picking karena bisa saja barang yang mau diterima hanya sebagian
                        price_unit = {}

                        for line in picking.move_ids_without_package:

                            if stock_move_id == None:
                                stock_move_id = line.id

                            product_id = line.product_id.id
                            line_qty = line.quantity if line.quantity > 0 else line.product_uom_qty

                            if product_id in po_details:
                                po_product = po_details[product_id]
                                po_qty = po_product['quantity']
                                po_price_subtotal = po_product['price_subtotal']

                                if product_id in po_details:
                                    po_product = po_details[product_id]
                                    po_qty = po_product['quantity']
                                    po_price_subtotal = po_product['price_subtotal']

                                    if line_qty <= po_qty:
                                        unit_value = po_price_subtotal * rate

                                        price_unit[product_id] = unit_value
                                        po_details[product_id]['quantity'] -= line_qty
                                    else:
                                        unit_value = po_price_subtotal * rate

                                        price_unit[product_id] = unit_value
                                        line_qty -= po_qty
                                        po_details[product_id]['quantity'] = 0

                        # Recalculate and update the stock valuation layers
                        journal_entry_ids = []

                        valuation_layers_to_update = self.env['stock.valuation.layer']
                        for line in picking.move_ids_without_package:
                            product_id = line.product_id.id
                            if product_id not in duplicate_product:
                                valuation_layers = self.env['stock.valuation.layer'].search([
                                    ('product_id', '=', product_id),
                                    ('reference', 'ilike', str(picking.name + "%"))
                                ])

                                for valuation_layer in valuation_layers:
                                    if product_id in price_unit:
                                        unit_value = price_unit[product_id]
                                        unit_value_new = (unit_value / valuation_layer.quantity) * valuation_layer.quantity
                                        valuation_layer.unit_cost = unit_value / valuation_layer.quantity
                                        valuation_layer.value = (unit_value / valuation_layer.quantity) * valuation_layer.quantity
                                        valuation_layer.remaining_value = valuation_layer.remaining_qty * (unit_value / valuation_layer.quantity)
                                        valuation_layers_to_update |= valuation_layer

                                        journal_entry = valuation_layer.account_move_id

                                        if journal_entry:
                                            for journal in journal_entry:
                                                for move_line in journal.line_ids:
                                                    with self.env.cr.savepoint():
                                                        move_line.with_context(check_move_validity=False).write({
                                                            'debit': unit_value_new if move_line.debit > 0 else move_line.debit,
                                                            'credit': unit_value_new if move_line.credit > 0 else move_line.credit,
                                                        })

                                                journal_entry_ids.append(journal.id)

                                                self.env.cr.execute("""
                                                        UPDATE account_move
                                                        SET name = '/',
                                                            state = 'draft',
                                                            date = %s,
                                                            sequence_prefix = '/',
                                                            sequence_number = 0
                                                        WHERE id = %s
                                                    """, (selected_date, journal.id))

                                                self.env.cr.commit()

                            elif product_id in duplicate_product:
                                valuation_layers = self.env['stock.valuation.layer'].search([
                                    ('product_id', '=', product_id),
                                    ('reference', 'ilike', str(picking.name + "%"))])

                                for valuation_layer in valuation_layers:
                                    if valuation_layer.account_move_id:
                                        valuation_layer.account_move_id.sudo().button_draft()
                                        valuation_layer.account_move_id.sudo().unlink()
                                    valuation_layer.sudo().unlink()

                        for product in po_details_duplicate_product:
                            # Avoid division by zero
                            if product['quantity'] > 0:
                                unit_cost = (product['price_subtotal'] / product['quantity']) * rate
                            else:
                                unit_cost = 0

                            # Create the valuation layer
                            new_valuation_layer = self.env['stock.valuation.layer'].sudo().create({
                                'product_id': product['product_id'],
                                'quantity': product['quantity'],
                                'remaining_qty': product['quantity'],
                                'unit_cost': unit_cost,
                                'value': product['price_subtotal'] * rate,
                                'company_id': picking.company_id.id,
                                'stock_move_id': stock_move_id,
                            })

                            # Then use SQL to update the create_date
                            self.env.cr.execute("""
                                UPDATE stock_valuation_layer
                                SET create_date = %s
                                WHERE id = %s
                            """, (selected_date, new_valuation_layer.id))

                            # Get the product once
                            prod = self.env['product.product'].browse(product['product_id'])

                            # Get the category once
                            product_category = prod.product_tmpl_id.categ_id

                            # Now use the cached product and category
                            journal_id = product_category.property_stock_journal.id

                            interim_stock_account_id = product_category.property_stock_account_input_categ_id.id
                            inventory_account_id = product_category.property_stock_valuation_account_id.id

                            move_vals = {
                                'ref': picking.name,
                                'journal_id': journal_id,
                                'date': selected_date,
                                'company_id': picking.company_id.id,
                                'line_ids': [
                                    (0, 0, {
                                        'name': f"{picking.name} - {prod.name}",
                                        'account_id': interim_stock_account_id,
                                        'partner_id': picking.partner_id.id,
                                        'debit': 0.0,
                                        'credit': product['price_subtotal'] * rate,
                                        'company_id': picking.company_id.id,
                                    }),
                                    (0, 0, {
                                        'name': f"{picking.name} - {prod.name}",
                                        'account_id': inventory_account_id,
                                        'partner_id': picking.partner_id.id,
                                        'debit': product['price_subtotal'] * rate,
                                        'credit': 0.0,
                                        'company_id': picking.company_id.id,
                                    })
                                ]
                            }

                            journal_entry = self.env['account.move'].sudo().create(move_vals)
                            journal_entry.sudo().action_post()

                            self.env.cr.execute("""
                                UPDATE stock_valuation_layer
                                SET account_move_id = %s
                                WHERE id = %s
                            """, (journal_entry.id, new_valuation_layer.id))

                            journal_entry_ids.append(journal_entry.id)

                            new_valuation_layer.account_move_id = journal_entry.id

                        # Change journal entry name by re-posting it again
                        if journal_entry_ids:
                            for journal_entry_id in journal_entry_ids:
                                account_move = self.env['account.move'].search([('id', '=', journal_entry_id)])

                                # Format the date components correctly
                                year = selected_date.year
                                month = str(selected_date.month).zfill(2)

                                new_sequence_prefix = f"{account_move.journal_id.code}/{year}/{month}/"

                                # Find the next available sequence number for this prefix
                                last_sequence = self.env['account.move'].search([
                                    ('sequence_prefix', '=', new_sequence_prefix),
                                ], order='sequence_number desc', limit=1)

                                new_sequence_number = (last_sequence.sequence_number or 0) + 1

                                # Format the sequence number string with adaptive padding
                                # If number is < 10000, pad to 4 digits, otherwise use as many digits as needed
                                if new_sequence_number < 10000:
                                    sequence_number_str = str(new_sequence_number).zfill(4)
                                else:
                                    sequence_number_str = str(new_sequence_number)

                                # Construct the complete new name
                                new_name = f"{new_sequence_prefix}{sequence_number_str}"

                                # Step 1: Set the state to draft using SQL
                                self.env.cr.execute("""
                                        UPDATE account_move
                                        SET state = 'draft'
                                        WHERE id = %s
                                    """, (account_move.id,))

                                # Step 3: Update the date and sequence information
                                self.env.cr.execute("""
                                        UPDATE account_move
                                        SET date = %s,
                                            sequence_prefix = %s,
                                            sequence_number = %s
                                        WHERE id = %s
                                    """, (selected_date, new_sequence_prefix, new_sequence_number, account_move.id))

                                self.env.cr.commit()

                                # Step 4: Finally update the name with the new formatted name
                                self.env.cr.execute("""
                                        UPDATE account_move
                                        SET name = %s
                                        WHERE id = %s
                                    """, (new_name, account_move.id))

                                # Set back to posted
                                self.env.cr.execute("""
                                        UPDATE account_move
                                        SET state = 'posted',
                                            made_sequence_gap = FALSE
                                        WHERE id = %s
                                    """, (account_move.id,))

                                # Set the flag to avoid sequence gap warnings
                                self.env.cr.execute("""
                                        UPDATE account_move
                                        SET made_sequence_gap = FALSE
                                        WHERE id = %s
                                    """, (account_move.id,))

                    # Recalculate the cost in produt template based on stock valuations
                    self.env.cr.commit()
                    self.action_update_valuation_layers(self.env['stock.picking'].browse(self._context.get('active_ids', [])))

            self.env.cr.commit()

            for move in picking.move_ids_without_package:
                # Get lots from move lines since lots are stored on move lines, not moves
                if move.lot_ids:

                    self.env.cr.execute("""
                            UPDATE stock_lot
                            SET create_date = %s
                            WHERE id IN %s
                        """, (picking.date_done, tuple(move.lot_ids.ids)))

                    valuation_layers = self.env['stock.valuation.layer'].search([
                        ('product_id', '=', move.product_id.id),
                        ('reference', 'ilike', picking.name + "%")
                    ])

                    for valuation_layer in valuation_layers:
                        if not valuation_layer.lot_id:
                            # Take the first lot from move lines
                            valuation_layer.lot_id = move.lot_ids[0]

                            self.env.cr.execute("""
                                UPDATE stock_lot
                                SET standard_price = to_jsonb(%s::numeric)
                                WHERE id IN %s
                            """, (valuation_layer.unit_cost, tuple(move.lot_ids.ids)))