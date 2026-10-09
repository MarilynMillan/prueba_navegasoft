import locale
from odoo import models, api, exceptions, fields
from num2words import num2words

class Contract(models.Model):
    _inherit = 'hr.contract'
    
    wage_to_word = fields.Text(compute="set_wage_to_word")
    date_start_contract = fields.Text(compute="set_date_start")
    pasante = fields.Boolean("Es pasante?")
    docente = fields.Boolean("Es docente?")
    variable = fields.Integer(compute="set_variable")
    variable_to_word = fields.Text(compute="set_variable_to_word")
    wage_docente = fields.Integer(compute="set_wage_docente")
    wage_to_word_docente = fields.Text(compute="set_wage_to_word_docente")
    

    def set_wage_docente(self):
        valor_comprobante =0
        for contract in self:
            cantidad = 0
            if contract.docente == True:
                #contrato_actual = payslip.contract_id
                payslips = self.env['hr.payslip'].search([('employee_id', '=', contract.employee_id.id),('state', '=', 'done'),('contract_id','=',contract.employee_id.contract_id.id)], limit=12, order='date_from desc')
                # payslip =  self.env["hr.payslip"].search(
                #     [("employee_id.id", "=", contract.employee_id.id), ("state", "=", "done")])
                cantidad = 0
                for payslip in payslips:
                    cantidad = cantidad + 1
                    print(payslip.name)
                    print(cantidad)
                    for line in payslip.line_ids:
                        
                        if line.salary_rule_id.code == "Basico":
                            valor_comprobante = line.total + valor_comprobante
                            
                            print(line.total)
                if cantidad > 0:
                    contract.wage_docente = valor_comprobante/cantidad
                    print(valor_comprobante)
                    print(cantidad)
                    print(contract.variable)
                else:
                    contract.wage_docente = 0
            else:
                contract.wage_docente = 0
            #contract.wage_to_word = num2words(c
        
        # for contract in self:
        #     contract.wage_to_word = num2words(contract.wage_docente, lang='es_CO')

    def set_wage_to_word_docente(self):
        for contract in self:
            if contract.docente == True:
                contract.wage_to_word_docente = num2words(contract.wage_docente, lang='es_CO')

    def set_variable(self):
        valor_comprobante =0
        for contract in self:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', contract.employee_id.id),('state', '=', 'done')], limit=12, order='date_from desc')
            # payslip =  self.env["hr.payslip"].search(
            #     [("employee_id.id", "=", contract.employee_id.id), ("state", "=", "done")])
            
            cantidad = 0
            for payslip in payslips:
                cantidad = cantidad + 1
                print(payslip.name)
                print(cantidad)
                for line in payslip.line_ids:
                    
                    if line.salary_rule_id.sueldo_variable == True:
                        valor_comprobante = line.total + valor_comprobante
                        
                        print(line.total)
            # if valor_comprobante > contract.wage:
            #     valor_variable = valor_comprobante - contract.wage
            # else:
            # valor_variable = 0

            if cantidad > 0:
                contract.variable = valor_comprobante/cantidad
                print(valor_comprobante)
                print(cantidad)
                print(contract.variable)
            else:
                contract.variable = 0
            #contract.wage_to_word = num2words(contract.wage, lang='es_CO')

    def set_variable_to_word(self):
        for contract in self:
            contract.variable_to_word = num2words(contract.variable, lang='es_CO')
            #contract.wage_to_word = num2words(contract.wage, lang='es_CO')
    
    def set_wage_to_word(self):
        ### si es docente agregar el promedio para los comprobantes
        for contract in self:
            contract.wage_to_word = num2words(contract.wage, lang='es_CO')
    
    @api.onchange("state", "employee_id")
    def to_disable_contracts(self):
        """Método impide tener mas de un contrato activo a la vez"""
        if self.state == "open":
            contracts = self.env["hr.contract"].search(
                [("employee_id.id", "=", self.employee_id.id), ("state", "=", "open")])
            if len(contracts) >= 1:
                raise exceptions.ValidationError("Actualmente tiene un contrato en ejecución")
    
    def write(self, vals):
        """ Sobreescritura del método que permite validar los cambios de estados de los contratos 
            para que nunca hallan mas de dos en ejecución """
        if 'state' in vals:
            if vals['state'] == "open":
                if 'employee_id' in vals:
                    contract = self.env["hr.contract"].search(
                        [("employee_id.id", "=", vals["employee_id"]), ("state", "=", "open")])
                    if len(contract) >= 1:
                        raise exceptions.ValidationError("Actualmente tiene un contrato en ejecución")
                else:
                    contract = self.env["hr.contract"].search(
                        [("employee_id.id", "=", self.employee_id.id), ("state", "=", "open")])
                    if len(contract) >= 1:
                        raise exceptions.ValidationError("Actualmente tiene un contrato en ejecución")

        super(Contract, self).write(vals)
        
    def set_date_start(self):
        """Establecer formato de fecha inicial para contrato"""
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8') #es_ES.UTF-8
        for contract in self:
            now = contract.date_start
            contract.date_start_contract = now.strftime('%d de %B del %Y').capitalize() if now else ''
