from functools import reduce
from odoo import models, fields, api,_
from datetime import datetime
import calendar
from odoo.exceptions import ValidationError
from collections import defaultdict
#from collections import defaultdictadd_grouped_lines

class ConsolidatePayroll(models.Model):
    _name = 'consolidated.payroll'
    _description = 'Consolidado de nómina'

    name = fields.Char(required=True, string="Nombre", readonly=False)#, states={'draft': [('readonly', False)]}
    state = fields.Selection([
        ('draft', 'Nuevo'),
        ('pending', 'Pendiente'),
        ('done', 'Consolidado')], string='Estado', index=True, readonly=True, copy=False, default='draft', store=True)
    month = fields.Selection([
        ('1', 'Enero'),
        ('2', 'Febrero'),
        ('3', 'Marzo'),
        ('4', 'Abril'),
        ('5', 'Mayo'),
        ('6', 'Junio'),
        ('7', 'Julio'),
        ('8', 'Agosto'),
        ('9', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre')
    ], string='Mes', required=True, readonly=False) #, states={'draft': [('readonly', False)]}
    year = fields.Selection(
        [(str(x), str(x)) for x in range(datetime.now().year, 2000, -1)], 
        string='Año',
        required=True, 
        readonly=False,
        #states={'draft': [('readonly', False)]}
    )
    payment_date=fields.Date(string='Fecha de Pago')
    start_date = fields.Date(string="Fecha desde", compute='_compute_start_date')
    end_date = fields.Date(string="Fecha hasta", compute='_compute_end_date')
    company_id = fields.Many2one('res.company', string='Compañia', readonly=True, required=True,
        default=lambda self: self.env.company)
    payslip_done_count = fields.Integer(compute='_compute_payslip_done_count')
    payslip_count = fields.Integer(compute='_compute_payslip_count')
    slip_ids = fields.One2many('hr.payslip', compute="_compute_slips_ids")
    rectified = fields.Boolean(
        string="Rectificación",
        help="¿El consolidado de nómina es una rectificación?",
        #states={'done': [('readonly', True)], 'pending': [('readonly', True)]}
        )
    consolidated_payroll_slips = fields.One2many('consolidated.payroll.slip', 'consolidated_payroll_id', string="Recibos consolidados")
    count_error = fields.Integer(string="Recibos con error", compute='count_error_consolidated_slips')
    def _compute_start_date(self):
        for payroll in self:
            payroll.start_date = datetime(int(payroll.year), int(payroll.month), 1)
    
    def _compute_end_date(self):
        for payroll in self:
            end_day_of_month = calendar.monthrange(int(payroll.year), int(payroll.month))
            payroll.end_date = datetime(int(payroll.year), int(payroll.month), end_day_of_month[1])

    def _compute_slips_ids(self):
        for payroll in self:
            domain = [
                ('date_from', '>=', payroll.start_date), 
                ('date_to', '<=', payroll.end_date), 
                ('rectified', '=', payroll.rectified),
                ('state', '!=', 'cancel')]
            payslips = self.env['hr.payslip'].sudo().search(domain)
            filtered_payslips = payslips.filtered(lambda slip: True if not self.env['consolidated.payroll.slip.assoc'].sudo().search([('slip_id', '=', slip.id)]) else False)
            payroll.slip_ids = filtered_payslips

    def _compute_payslip_count(self):
        for payroll in self:
            domain = [
                ('date_from', '>=', payroll.start_date), 
                ('date_to', '<=', payroll.end_date), 
                ('rectified', '=', payroll.rectified),
                ('state', '!=', 'cancel')]
            payslips = self.env['hr.payslip'].sudo().search(domain)
            filtered_payslips = payslips.filtered(lambda slip: True if not self.env['consolidated.payroll.slip.assoc'].sudo().search([('slip_id', '=', slip.id)]) else False)
            payroll.payslip_count = len(filtered_payslips)

    def _compute_payslip_done_count(self):
        for payroll in self:
            if payroll.state != 'done':
                payroll.payslip_done_count = 0
                continue
            payroll.payslip_done_count = self.env['consolidated.payroll.slip'].sudo().search_count([('consolidated_payroll_id', '=', payroll.id)])

    def add_grouped_lines(self, slip_employee, grouped_lines):
        for line in slip_employee.line_ids:
            data = {
                'name': line.name,
                'code': line.code,
                'sequence': line.sequence,
                'salary_rule_id': line.salary_rule_id.id,
                'category_id': line.category_id.id,
                'contract_id': line.contract_id.id,
                'employee_id': line.employee_id.id,
                'rate': line.rate,
                'amount': line.amount,
                'quantity': line.quantity,
                'total': line.total,
                'date_from': self.start_date,
                'date_to': self.end_date,
                'company_id': line.company_id.id,
                'currency_id': line.currency_id.id,
                'appears_on_payslip': line.appears_on_payslip
            }
            if line.salary_rule_id.code not in grouped_lines:
                grouped_lines[line.salary_rule_id.code] = [data]
            else:
                grouped_lines[line.salary_rule_id.code].append(data)

    def sum_grouped_lines(self, grouped_lines, emp_lines):
        for rule_id, lines in grouped_lines.items():
            quantity = 0
            amount = 0
            rate = 0
            total = 0
            first_line = lines[0]
                
            for line in lines:
                quantity += line['quantity']
                amount += line['amount']
                rate += line['rate']
                total += line['total']

            rate = rate/len(lines)
            first_line.update({
                'quantity': quantity,
                'rate': rate,
                'amount': amount,
                'total': total
            })
            emp_lines.append(first_line)

    def add_grouped_worked_days(self, slip_employee, grouped_worked_days):
        for day in slip_employee.worked_days_line_ids:
            data = {
                'name': day.name,
                'code': day.code,
                'sequence': day.sequence,
                'work_entry_type_id': day.work_entry_type_id.id,
                'number_of_days': day.number_of_days,
                'number_of_hours': day.number_of_hours,
                'contract_id': day.contract_id.id,
                'is_paid': day.is_paid,
                'currency_id': day.currency_id.id,
            }
            if day.work_entry_type_id.id not in grouped_worked_days:
                grouped_worked_days[day.work_entry_type_id.id] = [data]
            else:
                grouped_worked_days[day.work_entry_type_id.id].append(data)

    def sum_grouped_worked_days(self, grouped_worked_days, emp_worked_days):
        for type_id, worked_days in grouped_worked_days.items():
            number_of_days = 0
            number_of_hours = 0
            first_day = worked_days[0]
                
            for day in worked_days:
                number_of_days += day['number_of_days']
                number_of_hours += day['number_of_hours']

            first_day.update({
                'number_of_days': number_of_days,
                'number_of_hours': number_of_hours
            })
            emp_worked_days.append(first_day)

    def add_grouped_inputs(self, slip_employee, grouped_inputs):
        for input in slip_employee.input_line_ids:
            data = {
                'name': input.name,
                'code': input.code,
                'sequence': input.sequence,
                'input_type_id': input.input_type_id.id,
                'amount': input.amount,
                'contract_id': input.contract_id.id,
            }
            if input.input_type_id.id not in grouped_inputs:
                grouped_inputs[input.input_type_id.id] = [data]
            else:
                grouped_inputs[input.input_type_id.id].append(data)

    def sum_grouped_inputs(self, grouped_inputs, emp_inputs):
        for type_id, inputs in grouped_inputs.items():
            amount = 0
            first_input = inputs[0]
                
            for input in inputs:
                amount += input['amount']

            first_input.update({
                'amount': amount
            })
            emp_inputs.append(first_input)

    def action_done(self):
        for payroll in self:
            if payroll.state == 'done':
                continue

            domain = [
                ('date_from', '>=', payroll.start_date), 
                ('date_to', '<=', payroll.end_date), 
                ('rectified', '=', payroll.rectified),
                ('state', '!=', 'cancel'),
                ('company_id', '=', payroll.company_id.id)
            ]
            payslips = self.env['hr.payslip'].sudo().search(domain)
            filtered_payslips = payslips.filtered(lambda slip: True if not self.env['consolidated.payroll.slip.assoc'].sudo().search([('slip_id', '=', slip.id)]) else False)

            if not len(filtered_payslips):
                raise ValidationError("No hay recibos por consolidar")
                
            filtered_states = filtered_payslips.filtered(lambda slip: slip.state in ['draft', 'verify'])
            if filtered_states:
                nombres = ', '.join(filtered_states.mapped('name'))
                raise ValidationError(f'Por favor marque los siguientes recibos como "Hecho" o "Pagado": {nombres}')

            # Consolidated payroll slip
            slips_by_emp = {}
            for slip in filtered_payslips:
                if slip.employee_id.id not in slips_by_emp:
                    slips_by_emp[slip.employee_id.id] = [slip]
                else:
                    slips_by_emp[slip.employee_id.id].append(slip)

            for emp_id, slips_emp in slips_by_emp.items():
                if not len(slips_emp):
                    continue
                
                first_slip = slips_emp[0]
                basic_wage = 0
                net_wage = 0
                slip_ids = []
                grouped_lines = {}
                grouped_worked_days = {}
                grouped_inputs = {}

                for slip_employee in slips_emp:
                    basic_wage += slip_employee.basic_wage
                    net_wage += slip_employee.net_wage
                    slip_ids.append(slip_employee.id)
                    self.add_grouped_lines(slip_employee, grouped_lines)
                    self.add_grouped_worked_days(slip_employee, grouped_worked_days)
                    self.add_grouped_inputs(slip_employee, grouped_inputs)
                
                emp_lines = []
                emp_worked_days = []
                emp_inputs = []
                
                self.sum_grouped_lines(grouped_lines, emp_lines)
                self.sum_grouped_worked_days(grouped_worked_days, emp_worked_days)
                self.sum_grouped_inputs(grouped_inputs, emp_inputs)

                number = self.env['ir.sequence'].next_by_code('consolidated.payroll.slip')
                data = {
                    'number': number,
                    'employee_id': first_slip.employee_id.id,
                    'department_id': first_slip.department_id.id,
                    'job_id': first_slip.job_id.id,
                    'date_from': self.start_date,
                    'date_to': self.end_date,
                    'contract_id': first_slip.contract_id.id,
                    'company_id': first_slip.company_id.id,
                    'country_id': first_slip.country_id.id,
                    'country_code': first_slip.country_code,
                    'basic_wage': basic_wage,
                    'net_wage': net_wage,
                    'currency_id': first_slip.currency_id.id,
                    'consolidated_payroll_id': self.id,
                    'struct_id': first_slip.struct_id.id,
                    'struct_type_id': first_slip.struct_type_id.id,
                    'wage_type': first_slip.wage_type
                }

                consolidated_payroll_slip = self.env['consolidated.payroll.slip'].sudo().create(data)

                for id in slip_ids:
                    data = {
                        'consolidated_id': consolidated_payroll_slip.id,
                        'slip_id': id
                    }
                    self.env['consolidated.payroll.slip.assoc'].sudo().create(data)

                for line in emp_lines:
                    line['slip_id'] = consolidated_payroll_slip.id
                    self.env['consolidated.payroll.slip.line'].sudo().create(line)

                for day in emp_worked_days:
                    day['payslip_id'] = consolidated_payroll_slip.id
                    self.env['consolidated.payroll.slip.worked.days'].sudo().create(day)

                for input in emp_inputs:
                    input['payslip_id'] = consolidated_payroll_slip.id
                    self.env['consolidated.payroll.slip.input'].sudo().create(input)

            # Consolidated payroll
            payroll.write({'state': 'done'})
    
    def action_open_payslips(self):
        """Ver recibos de nómina"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "list"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "context": {'group_by':'employee_id'},
            "name": "Recibos de nómina",
        }

    def action_open_payslips_done(self):
        """Ver recibos de nómina consolidados"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "consolidated.payroll.slip",
            "views": [[False, "list"], [False, "form"]],
            "domain": [['consolidated_payroll_id', '=', self.id]],
            "name": "Consolidados",
        }
    
    def action_unlink(self):
        """Eliminar consolidado"""
        for payroll in self:
            if payroll.state == 'done':
                raise ValidationError("El periodo ya ha sido consolidado")
            payroll.unlink()

        return {
            "type": "ir.actions.act_window",
            "res_model": "consolidated.payroll",
            "views": [[False, "list"], [False, "form"]],
            "target": "main",
            "name": "Consolidado de nómina",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['state'] = 'pending'
            """
            has_period = self.env['consolidated.payroll'].sudo().search([
                ('year', '=', vals['year']),
                ('month', '=', vals['month']),
                ('rectified', '=', False)
            ])

            if has_period and vals['rectified'] is False:
                raise ValidationError("Ya existe un consolidado con este periodo")
            """
        records = super(ConsolidatePayroll, self).create(vals_list)
        return records

    def unlink(self):
        """Eliminar consolidados"""
        for payroll in self:
            if payroll.state == 'done':
                raise ValidationError("Algunos registros no se pueden eliminar porque ya estan consolidados")
        return super(ConsolidatePayroll, self).unlink()

    def count_error_consolidated_slips(self):
        """Contar recibos consolidados con error"""
        for payroll in self:
            slips_with_error = payroll.consolidated_payroll_slips.filtered(lambda s: s.error)
            payroll.count_error = len(slips_with_error)
            

    

    def action_rectify(self):
        """Rectificar nómina: agrupa líneas por código"""
        for payroll in self:
            slips_with_error = payroll.consolidated_payroll_slips.filtered(lambda s: s.error)
            if not slips_with_error:
                raise ValidationError("No hay recibos con error para rectificar")
            for slip in slips_with_error:
                # Agrupar líneas por 'code'
                grouped = defaultdict(lambda: {
                    'name': '',
                    'code': '',
                    'category_id': None,
                    'quantity': 0.0,
                    'rate': 0.0,
                    'rule_id': None,
                    'amount': 0.0,
                    'total': 0.0,
                })

                for line in slip.line_ids:
                    key = line.code
                    grouped[key]['name'] = line.name
                    grouped[key]['code'] = line.code
                    grouped[key]['category_id'] = line.category_id.id
                    grouped[key]['quantity'] += line.quantity
                    grouped[key]['rate'] = line.rate
                    grouped[key]['salary_rule_id'] = line.salary_rule_id.id
                    grouped[key]['amount'] += line.amount
                    grouped[key]['total'] += line.total

                # Eliminar líneas actuales
                slip.line_ids.unlink()

                # Crear nuevas líneas agrupadas
                for values in grouped.values():
                    slip.line_ids.create({
                        'slip_id': slip.id,
                        'name': values['name'],
                        'code': values['code'],
                        'category_id': values['category_id'],
                        'quantity': values['quantity'],
                        'rate': values['rate'],
                        'salary_rule_id': values['salary_rule_id'],
                        'amount': values['amount'],
                        'total': values['total'],
                    })
                # Actualizar el total del recibo
                #slip.total = sum(line.total for line in slip.line_ids)
               # slip.write({'error': False})
               # slip.message_post(body="Recibo rectificado y líneas agrupadas por código.")
                   
    def _get_assoc_source_payslips(self):
        """
        Devuelve todos los hr.payslip fuente usados en ESTE consolidado,
        leyendo la tabla de asociación consolidated.payroll.slip.assoc.
        """
        self.ensure_one()
        Assoc = self.env['consolidated.payroll.slip.assoc'].sudo()
        # 'consolidated_id' en la tabla assoc apunta a consolidated.payroll.slip
        assoc = Assoc.search([('consolidated_id', 'in', self.consolidated_payroll_slips.ids)])
        slip_ids = assoc.mapped('slip_id')
        return self.env['hr.payslip'].sudo().browse(slip_ids)


    def action_reconsolidate_new(self):
        """
        Crea un NUEVO consolidated.payroll con los mismos hr.payslip que ya
        participaron en este consolidado y crea nuevos consolidated.payroll.slip,
        dejando en cada uno el 'consolidated_id' apuntando al slip anterior.
        """
        assoc = self.env['consolidated.payroll.slip.assoc'].sudo()
        self.ensure_one()
        if self.state != 'done':
            raise ValidationError(_("Primero consolida este período (estado 'Consolidado')."))

        sources = self._get_assoc_source_payslips()
        if not sources:
            raise ValidationError(_("No se encontraron recibos fuente asociados a este consolidado."))

        # Nuevo encabezado
        new_vals = {
            'name': _("%s - Rectificación") % (self.name or ''),
            'state': 'draft',
            'month': self.month,
            'year': self.year,
            'payment_date': self.payment_date,
            'company_id': self.company_id.id,
            'rectified': True,
        }
        new_cp = self.create(new_vals)

        # Mapa empleado -> consolidated.payroll.slip anterior (de este consolidado origen)
        # Si hay más de uno por empleado, tomamos el primero encontrado.
        origin_by_emp = {}
        for old_slip in self.consolidated_payroll_slips:
            origin_by_emp.setdefault(old_slip.employee_id.id, old_slip)

        # Agrupar fuentes por empleado (¡ojo: iteramos records, NO ids!)
        from collections import defaultdict
        slips_by_emp = defaultdict(list)
        for slip in sources.ids:
            slips_by_emp[slip.employee_id.id].append(slip)

        # Reconstruir cada nuevo consolidated.payroll.slip
        for emp_id, slips_emp in slips_by_emp.items():
            if not slips_emp:
                continue

            first_slip = slips_emp[0]
            basic_wage = sum(s.basic_wage for s in slips_emp)
            net_wage = sum(s.net_wage for s in slips_emp)

            grouped_lines, grouped_worked_days, grouped_inputs = {}, {}, {}
            for src in slips_emp:
                new_cp.add_grouped_lines(src, grouped_lines)
                new_cp.add_grouped_worked_days(src, grouped_worked_days)
                new_cp.add_grouped_inputs(src, grouped_inputs)

            emp_lines, emp_worked_days, emp_inputs = [], [], []
            new_cp.sum_grouped_lines(grouped_lines, emp_lines)
            new_cp.sum_grouped_worked_days(grouped_worked_days, emp_worked_days)
            new_cp.sum_grouped_inputs(grouped_inputs, emp_inputs)

            number = self.env['ir.sequence'].next_by_code('consolidated.payroll.slip')

            # Localizamos el slip anterior del mismo empleado para enlazarlo
            origin_slip = origin_by_emp.get(emp_id)
            
            
            slip_vals = {
                'number': number,
                'employee_id': first_slip.employee_id.id,
                'department_id': first_slip.department_id.id,
                'job_id': first_slip.job_id.id,
                'date_from': new_cp.start_date,
                'date_to': new_cp.end_date,
                'contract_id': first_slip.contract_id.id,
                'company_id': first_slip.company_id.id,
                'country_id': first_slip.country_id.id,
                'country_code': first_slip.country_code,
                'basic_wage': basic_wage,
                'net_wage': net_wage,
                'currency_id': first_slip.currency_id.id,
                'consolidated_payroll_id': new_cp.id,
                'struct_id': first_slip.struct_id.id,
                'struct_type_id': first_slip.struct_type_id.id,
                'wage_type': first_slip.wage_type,
                'fecha_pago': new_cp.payment_date,
                # aquí dejamos enlazado el anterior:
                
                'consolidated_id': origin_slip.id if origin_slip else False,
                'cune':origin_slip.cune if origin_slip else False,
                'id_plataforma': origin_slip.id_plataforma if origin_slip else False,
                'NIT': origin_slip.NIT if origin_slip else False,
                'DV': origin_slip.DV if origin_slip else False,
                'OtrosNombres': origin_slip.OtrosNombres if origin_slip else False,
                'PrimerNombre': origin_slip.PrimerNombre if origin_slip else False,
                'PrimerApellido': origin_slip.PrimerApellido if origin_slip else False,
                'SegundoApellido': origin_slip.SegundoApellido if origin_slip else False,
                'Algoritmo': origin_slip.Algoritmo if origin_slip else False,
                'tipoXML': origin_slip.tipoXML if origin_slip else False,
                'transaccionID': origin_slip.transaccionID if origin_slip else False,
                'credit_note':True,
            }
            new_consolidated_slip = self.env['consolidated.payroll.slip'].sudo().create(slip_vals)
            slips_emp_ids = assoc.create([{'consolidated_id': origin_slip.id, 'slip_id': s.id} for s in slips_emp if origin_slip])
            new_consolidated_slip.write({'assoc_slips': [(6, 0, slips_emp_ids.ids)]})
            # Líneas
            Line = self.env['consolidated.payroll.slip.line'].sudo()
            for line in emp_lines:
                vals = dict(line)
                vals['slip_id'] = new_consolidated_slip.id
                Line.create(vals)

            # Días trabajados
            Worked = self.env['consolidated.payroll.slip.worked.days'].sudo()
            for day in emp_worked_days:
                vals = dict(day)
                vals['payslip_id'] = new_consolidated_slip.id
                Worked.create(vals)

            # Inputs
            Input = self.env['consolidated.payroll.slip.input'].sudo()
            for inp in emp_inputs:
                vals = dict(inp)
                vals['payslip_id'] = new_consolidated_slip.id
                Input.create(vals)

        # Estado final
        new_cp.write({'state': 'done'})

        # Abrir el nuevo consolidado
        return {
            "type": "ir.actions.act_window",
            "res_model": "consolidated.payroll",
            "views": [[False, "form"]],
            "res_id": new_cp.id,
            "target": "current",
            "name": _("Consolidado de nómina (nuevo)"),
        }

    def action_reconsolidate_new_nocredit(self):
        """
        Crea un NUEVO consolidated.payroll con los mismos hr.payslip que ya
        participaron en este consolidado y crea nuevos consolidated.payroll.slip,
        dejando en cada uno el 'consolidated_id' apuntando al slip anterior.
        """
        assoc = self.env['consolidated.payroll.slip.assoc'].sudo()
        self.ensure_one()
        if self.state != 'done':
            raise ValidationError(_("Primero consolida este período (estado 'Consolidado')."))

        sources = self._get_assoc_source_payslips()
        if not sources:
            raise ValidationError(_("No se encontraron recibos fuente asociados a este consolidado."))

        # Nuevo encabezado
        new_vals = {
            'name': _("%s -Reagrupado") % (self.name or ''),
            'state': 'draft',
            'month': self.month,
            'year': self.year,
            'payment_date': self.payment_date,
            'company_id': self.company_id.id,
           # 'rectified': True,
        }
        new_cp = self.create(new_vals)

        # Mapa empleado -> consolidated.payroll.slip anterior (de este consolidado origen)
        # Si hay más de uno por empleado, tomamos el primero encontrado.
        origin_by_emp = {}
        for old_slip in self.consolidated_payroll_slips:
            origin_by_emp.setdefault(old_slip.employee_id.id, old_slip)

        # Agrupar fuentes por empleado (¡ojo: iteramos records, NO ids!)
        from collections import defaultdict
        slips_by_emp = defaultdict(list)
        for slip in sources.ids:
            slips_by_emp[slip.employee_id.id].append(slip)

        # Reconstruir cada nuevo consolidated.payroll.slip
        for emp_id, slips_emp in slips_by_emp.items():
            if not slips_emp:
                continue

            first_slip = slips_emp[0]
            basic_wage = sum(s.basic_wage for s in slips_emp)
            net_wage = sum(s.net_wage for s in slips_emp)

            grouped_lines, grouped_worked_days, grouped_inputs = {}, {}, {}
            for src in slips_emp:
                new_cp.add_grouped_lines(src, grouped_lines)
                new_cp.add_grouped_worked_days(src, grouped_worked_days)
                new_cp.add_grouped_inputs(src, grouped_inputs)

            emp_lines, emp_worked_days, emp_inputs = [], [], []
            new_cp.sum_grouped_lines(grouped_lines, emp_lines)
            new_cp.sum_grouped_worked_days(grouped_worked_days, emp_worked_days)
            new_cp.sum_grouped_inputs(grouped_inputs, emp_inputs)

            number = self.env['ir.sequence'].next_by_code('consolidated.payroll.slip')

            # Localizamos el slip anterior del mismo empleado para enlazarlo
            origin_slip = origin_by_emp.get(emp_id)
            
            
            slip_vals = {
                'number': number,
                'employee_id': first_slip.employee_id.id,
                'department_id': first_slip.department_id.id,
                'job_id': first_slip.job_id.id,
                'date_from': new_cp.start_date,
                'date_to': new_cp.end_date,
                'contract_id': first_slip.contract_id.id,
                'company_id': first_slip.company_id.id,
                'country_id': first_slip.country_id.id,
                'country_code': first_slip.country_code,
                'basic_wage': basic_wage,
                'net_wage': net_wage,
                'currency_id': first_slip.currency_id.id,
                'consolidated_payroll_id': new_cp.id,
                'struct_id': first_slip.struct_id.id,
                'struct_type_id': first_slip.struct_type_id.id,
                'wage_type': first_slip.wage_type,
               # 'fecha_pago': new_cp.payment_date,
                # aquí dejamos enlazado el anterior:
                
                'consolidated_id': origin_slip.id if origin_slip else False,
                'cune':origin_slip.cune if origin_slip else False,
                'id_plataforma': origin_slip.id_plataforma if origin_slip else False,
                'NIT': origin_slip.NIT if origin_slip else False,
                'DV': origin_slip.DV if origin_slip else False,
                'OtrosNombres': origin_slip.OtrosNombres if origin_slip else False,
                'PrimerNombre': origin_slip.PrimerNombre if origin_slip else False,
                'PrimerApellido': origin_slip.PrimerApellido if origin_slip else False,
                'SegundoApellido': origin_slip.SegundoApellido if origin_slip else False,
                'Algoritmo': origin_slip.Algoritmo if origin_slip else False,
                'tipoXML': origin_slip.tipoXML if origin_slip else False,
                'transaccionID': origin_slip.transaccionID if origin_slip else False,
               # 'credit_note':True,
            }
            new_consolidated_slip = self.env['consolidated.payroll.slip'].sudo().create(slip_vals)
            slips_emp_ids = assoc.create([{'consolidated_id': origin_slip.id, 'slip_id': s.id} for s in slips_emp if origin_slip])
            new_consolidated_slip.write({'assoc_slips': [(6, 0, slips_emp_ids.ids)]})
            # Líneas
            Line = self.env['consolidated.payroll.slip.line'].sudo()
            for line in emp_lines:
                vals = dict(line)
                vals['slip_id'] = new_consolidated_slip.id
                Line.create(vals)

            # Días trabajados
            Worked = self.env['consolidated.payroll.slip.worked.days'].sudo()
            for day in emp_worked_days:
                vals = dict(day)
                vals['payslip_id'] = new_consolidated_slip.id
                Worked.create(vals)

            # Inputs
            Input = self.env['consolidated.payroll.slip.input'].sudo()
            for inp in emp_inputs:
                vals = dict(inp)
                vals['payslip_id'] = new_consolidated_slip.id
                Input.create(vals)

        # Estado final
        new_cp.write({'state': 'done'})

        # Abrir el nuevo consolidado
        return {
            "type": "ir.actions.act_window",
            "res_model": "consolidated.payroll",
            "views": [[False, "form"]],
            "res_id": new_cp.id,
            "target": "current",
            "name": _("Consolidado de nómina (nuevo)"),
        }