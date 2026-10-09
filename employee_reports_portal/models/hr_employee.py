from odoo import models, fields, exceptions, api
from odoo import _
import locale, datetime

class Employee(models.Model):
    _inherit = "hr.employee"

    type_document = fields.Selection([
        ('rut', 'NIT'),
        ('id_document', 'Cédula'),
        ('id_card', 'Tarjeta de identidad'),
        ('passport', 'Pasaporte'),
        ('foreign_id_card', 'Cédula extranjera'),
        ('external_id', 'ID del exterior'),
        ('diplomatic_card', 'Carné diplomatico'),
        ('residence_document', 'Salvoconducto de permanencia'),
        ('civil_registration', 'Registro civil'),
        ('national_citizen_id', 'Cédula de ciudadanía')], string="Document type", default="id_document")

    current_contract = fields.Many2one("hr.contract", compute="contract_actual", string="Current contract")
    message_contract = fields.Char(string="Current contract", default="Actualmente no hay contratos vigentes")
    firm = fields.Image(string="Firm")
    payroll_manager = fields.Many2one("hr.employee", string="Payroll Manager", compute="set_payroll_manager")
    date_now = fields.Text(compute="set_date_now")
    start_date_current_contract = fields.Text(compute="set_date_start")
    firm_url =  fields.Text(compute="set_firm_url")
    
    employee_functions = fields.One2many('hr.employee.functions', 'employee_id', 'Functions')

    program_ids = fields.Many2many(
        'hr.employee.program', 'employee_program_rel',
        'employee_id', 'program_id', groups="hr.group_hr_user",
        string='Programs')
    
    text_working = fields.Char(string="",default="laboró" )
    text_working2 = fields.Char(string="",default="en el progrzama de " )
    end_date_contract = fields.Char(compute="set_date_end")
    
    def contract_actual(self):
        """Método llamado por la declaración del atributo current_contract como campo calculado, que indexa el contrato actual al campo"""
        for employee in self:
            contract = self.env["hr.contract"].search([("employee_id.id", "=", employee.id), ("state", "in", ["open", "close", "cancel"])], order="date_start desc")
            
            if not contract:
                employee.current_contract = None
            if len(contract) > 1:
                contract = sorted(contract, key=lambda c: 0 if c.state == 'open' else 1)
                employee.current_contract = contract[0]
            else:
                employee.current_contract = contract

    @api.onchange("user_id")
    def change_user_id(self):
        """Método que valida que un usuario solo pueda estar asignado a un empleado"""
        employee = self.env["hr.employee"].search([("user_id.id", "=", self.user_id.id)])
        if employee:
            if employee.id != self._origin.id:
                raise exceptions.ValidationError("No puede asignar el usuario")

    def set_payroll_manager(self):
        """Método llamado por la declaración del atributo payroll_manager como campo calculado, que indexa el empleado que es gerente de nomina"""
        payroll_manage = self.env['ir.config_parameter'].search([]).get_param('res.config.settings.payroll_manager')
        n = ""
        if payroll_manage != False:
            for caracter in payroll_manage:
                try:
                    n = n + str(int(caracter))
                except:
                    raise exceptions.ValidationError("No es un carácter valido")
            for employee in self:
                employee.payroll_manager = self.env["hr.employee"].browse(int(n))
        else:
            for employee in self:
                employee.payroll_manager = self.env["hr.employee"].browse(int(payroll_manage))

    def set_date_now(self):
        """Método llamado por la declaración del atributo date_now como campo calculado, que almacena la fecha actual con formato colombiano en el campo"""
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8') #es_ES.UTF-8
        now = datetime.datetime.now()
        for employee in self:
            employee.date_now = now.strftime('%d de %B del %Y').capitalize()

    def set_date_start(self):
        """Método llamado por la declaración del atributo start_date_current_contract como campo calculado, que almacena la fecha del inicio del contrato con formato colombiano"""
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8') #es_ES.UTF-8
        for employee in self:
            if employee.current_contract.date_start:
                now = employee.current_contract.date_start
                employee.start_date_current_contract = now.strftime('%d de %B del %Y').capitalize()
                
    def set_firm_url(self):
        """Método llamado por firm_url como campo calculado, que obtiene la imagen codificada en base64"""
        for employee in self:
            if employee.firm:
                employee.firm_url = employee.firm.decode('utf-8')
                
    def contract_list(self):
        """Obtener listado de contratos"""
        for employee in self:
            contract = self.env["hr.contract"].search([("employee_id.id", "=", employee.id), ("state", "in", ["open", "close", "cancel"])], order="date_start desc")
            return contract
        
    def first_contract(self):
        """Obtener primer contrato"""
        for employee in self:
            contract = self.env["hr.contract"].search([("employee_id.id", "=", employee.id), ("state", "in", ["open", "close", "cancel"])], order="date_start asc")
            return contract[0] if contract else False
        
    def program_list(self):
        """Obtener listado de programas"""
        for employee in self:
            programs = []
            for program in employee.program_ids:
                programs.append(program.name.strip())
            return ' Y '.join(programs)
        
    def check_current_contract(self):
        """Revisa el último contrato del empleado"""
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
        today = datetime.datetime.today().date()
        contract = self.env['hr.contract'].search([('employee_id', '=', self.id)], order='date_start desc', limit=1)
        print(contract)
        if contract:
            if not contract.date_end or contract.date_end >= today:
                if contract.pasante:
                    return 'realiza su etapa de prácticas'
                else:
                    return 'labora'
            else:
                if contract.pasante:
                    return 'realizó su etapa de prácticas'
                else:
                    return 'laboró' 
        else:
            return 'laboró'

    def check_current_contract2(self):
        """Revisa el último contrato del empleado"""
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
        today = datetime.datetime.today().date()
        # contract = self.env['hr.contract'].search([('employee_id', '=', self.id)], order='date_start desc', limit=1)
        print(self.program_ids)
        cantidad_programas = 0
        texto_programas = ""
        texto = ""
        for programa in self.program_ids:
            cantidad_programas = cantidad_programas + 1
            if len(self.program_ids) == cantidad_programas:
                texto_programas = texto_programas + " " +programa.name+ "," 
            else:
                texto_programas = texto_programas +" "+programa.name+ "," 

        if cantidad_programas == 1:
            texto = texto_programas
        elif cantidad_programas > 1:
            texto = texto_programas
        elif cantidad_programas == 0:
            texto = " "

        
        return texto

    def set_date_end(self):
        """Método llamado por la declaración del atributo end_date_contract como campo calculado, que almacena la fecha del fin del contrato con formato colombiano"""
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
        today = datetime.datetime.today().date()
        for employee in self:
            contract = self.env['hr.contract'].search([('employee_id', '=', employee.id)], order='date_start desc', limit=1)
            if contract:
                if not contract.date_end or contract.date_end >= today:
                    employee.end_date_contract = ''
                else:
                    employee.end_date_contract = ' hasta el ' + contract.date_end.strftime('%d de %B del %Y')
            else: 
                employee.end_date_contract = ''
            
    
