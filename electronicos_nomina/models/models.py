
from odoo import models, fields, api
from datetime import datetime, timedelta
import os
import requests
import json 
from odoo.exceptions import AccessError, UserError,  ValidationError
from odoo.tools.safe_eval import safe_eval

class electronicos_nomina(models.Model):
    _inherit = 'base_electronicos.tabla'
    _description = 'base_electronicos'
    # _inherit = 'mail.message'
    
    generales_id = fields.One2many('electronicos_nomina.datos_generales','general_id', ondelete='cascade')

class datos_generales(models.Model):
    _name= 'electronicos_nomina.datos_generales'
    _descripcion='electronicos_nomina.datos_generales'

    name = fields.Char("Nombre")
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False,
        default=lambda self: self.env['res.company']._company_default_get())
        #states={'draft': [('readonly', False)]})
    fecha_pago = fields.Date("Fecha de Pago")   
    xml = fields.Text("XML")
    transaccionID = fields.Char("transaccionID")
    impreso = fields.Boolean("Impreso")
    prefijo = fields.Char("Prefijo")
    consecutivo = fields.Char("consecutivo")
    paisgeneracion = fields.Char("Pais de generacion")
    departamentoestado = fields.Char("Departamento")
    municipiociudad = fields.Char("Ciudad")
    Idioma = fields.Char("Idioma",default="es")
    
    version = fields.Char("Version",default="")
    ambiente = fields.Selection([
        ('1', 'Produccion'),
        ('2', 'Pruebas'),
    ], string='Ambiente',default="1")
    tipoXML = fields.Char("Tipo XML",default="102")
    Algoritmo = fields.Char("Algoritmo",default="CUNE-384")
    PeriodoNomina = fields.Selection([
        ('1', 'Semanal'),
        ('2', 'Decenal'),
        ('3', 'Catorcenal'),
        ('4', 'Quincenal'),
        ('5', 'Mensual'),
    ], string='Periodo Nomina')
    TipoMoneda = fields.Char('TipoMoneda', default="COP") 
    ##EMPLEADOR
    RazonSocial = fields.Char('RazonSocial')    
    PrimerApellido = fields.Char('PrimerApellido')
    SegundoApellido = fields.Char('SegundoApellido')
    PrimerNombre = fields.Char('PrimerNombre')
    OtrosNombres = fields.Char('OtrosNombres') 
    NIT = fields.Char('NIT') 
    DV = fields.Char('DV')
    PaisEmpleador = fields.Char('Pais')
    MunicipioCiudadEmpleador = fields.Char('MunicipioCiudad')
    DepartamentoEstadoEmpleador = fields.Char('DepartamentoEstado') 
    DireccionEmpleador = fields.Char('Direccion') 

    tipocontrato = fields.Selection([
        ('1', 'Termino Fijo'),
        ('2', 'Termino Indefinido'),
        ('3', 'Obra o Labor'),
        ('4', 'Aprendizaje'),
        ('5', 'Practicas'),
    ], string='Tipo de contrato')

    id_plataforma = fields.Char('id_plataforma')
    password = fields.Char('password')
    general_id = fields.Many2one('base_electronicos.tabla', string='Campos',ondelete='restrict', index=True)


class nomina_input_lines(models.Model):
    _name = 'hr.salary.rule'
    _inherit = 'hr.salary.rule'

    porcentaje = fields.Char("Porcentaje")


class nomina_electronica(models.Model):
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'

    nota_credito = fields.Selection([('Eliminar', 'Eliminar'), ('Modificar', 'Modificar')], string='Tipo de nota' ,required=False,default='Eliminar')
    CUNEPred = fields.Char("CUNE")
    NumeroPred = fields.Char("Numero Anterior")
    FechaGenPred = fields.Date("Fecha de Predecesor")   
    causa = fields.Char("Causa")
    fecha_pago = fields.Date("Fecha de Pago")   
    xml = fields.Text("XML")
    transaccionID = fields.Char("transaccionID")
    estado = fields.Selection([
        ('no_generada', 'No_generada'),
        ('Generada_correctamente', 'Generada_correctamente'),
        ('Generada_con_errores', 'Con_errores'),
    ], string='Estado',default="no_generada")
    prefijo = fields.Char("Prefijo")
    consecutivo = fields.Char("consecutivo")
    paisgeneracion = fields.Char("Pais de generacion")
    departamentoestado = fields.Char("Departamento")
    municipiociudad = fields.Char("Ciudad")
    Idioma = fields.Char("Idioma",default="es")
    impreso = fields.Boolean("Impreso")
    version = fields.Char("Version",default="")
    ambiente = fields.Selection([
        ('1', 'Produccion'),
        ('2', 'Pruebas'),
    ], string='Ambiente',default="1")
    tipoXML = fields.Char("Tipo XML",default="102")
    Algoritmo = fields.Char("Algoritmo",default="CUNE-384")
    PeriodoNomina = fields.Selection([
        ('1', 'Semanal'),
        ('2', 'Decenal'),
        ('3', 'Catorcenal'),
        ('4', 'Quincenal'),
        ('5', 'Mensual'),
    ], string='Periodo Nomina')
    TipoMoneda = fields.Char('TipoMoneda', default="COP") 
    Notas = fields.Char('Notas')
    ##EMPLEADOR
    RazonSocial = fields.Char('RazonSocial')    
    PrimerApellido = fields.Char('PrimerApellido')
    SegundoApellido = fields.Char('SegundoApellido')
    PrimerNombre = fields.Char('PrimerNombre')
    OtrosNombres = fields.Char('OtrosNombres') 
    NIT = fields.Char('NIT') 
    DV = fields.Char('DV')
    PaisEmpleador = fields.Char('Pais')
    MunicipioCiudadEmpleador = fields.Char('MunicipioCiudad')
    DepartamentoEstadoEmpleador = fields.Char('DepartamentoEstado') 
    DireccionEmpleador = fields.Char('Direccion') 

    tipocontrato = fields.Selection([
        ('1', 'Termino Fijo'),
        ('2', 'Termino Indefinido'),
        ('3', 'Obra o Labor'),
        ('4', 'Aprendizaje'),
        ('5', 'Practicas'),
    ], string='Tipo de contrato')
    
    FechaGen = fields.Char('Fecha Generacion')
    HoraGen = fields.Char('Hora Generacion')
    id_plataforma = fields.Char('id_plataforma')
    password = fields.Char('password')
    cune = fields.Char('CUNE')
    error = fields.Char('Error')
    solucion = fields.Char('Solucion')
    # PeriodoNomina = fields.Char('Periodo Nomina') 
    # TipoMoneda = fields.Char('TipoMoneda', default="COP") 
    # input_line_ids = fields.One2many(
    #     'hr.payslip.input', 'payslip_id', string='Payslip Inputs',
    #     compute='_compute_input_line_ids', store=True,copy='True',
    #     readonly=False #, states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]}
    #     )
    # Notas = fields.Char('Notas')    


    ##contrain numero de nomina
    @api.constrains('number')
    def _check_number(self):
        for record in self:
            cantidad = self.env['hr.payslip'].search([('number', '=', self.number)])
            print(cantidad)
            print(len(cantidad))
            if len(cantidad) > 1:
                raise ValidationError("Existe un comprobante con el mismo numero, por favor modifique el consecutivo de la nomina "+cantidad[0].number)

    def copy(self, default=None):
        default = dict(default or {})
        default.update({'estado': 'no_generada','transaccionID': '','consecutivo': ''})
        return super(nomina_electronica, self).copy(default)

    def unlink(self, default=None):
        for payslip in self:
            if payslip.estado == 'Generada_correctamente':
                raise UserError('No se puede eliminar una nomina que ya ha sido generada')
        return super(nomina_electronica, self).unlink()    
    
    #@api.multi
    def compute_refund(self,causa,tipo_nota):
        copied_payslips = self.env['hr.payslip']
        for payslip in self:
            numero_pred = payslip.prefijo+payslip.consecutivo
            fecha_gen_pred = payslip.FechaGen
            CUNEPred = payslip.cune
            # if payslip.number:
            #     number = payslip.number
            # else:
            number = self.env['ir.sequence'].next_by_code('salary.refund')
            
            numbersequence = self.env['ir.sequence'].search([('code', '=', 'salary.refund')])
            prefijo = numbersequence.prefix
            if not prefijo:
                raise UserError('No existe un prefijo en la configuracion de la nota credito de la nomina se configura en la secuencia salary.refund')
            longitudprefijo = len(prefijo)
            longitudsecuencia = len(number)
            consecutivo = number[longitudprefijo:longitudsecuencia]
            print("number")
            print(number)
            copied_payslip = payslip.copy({
                'credit_note': True,
                'name': number,
                'edited': True,
                'state': 'verify', 'number': number,'transaccionID':'',
                        'estado':'no_generada','nota_credito':tipo_nota,'causa':causa,
                        'CUNEPred':CUNEPred,'NumeroPred':numero_pred,'FechaGenPred':fecha_gen_pred,
                        'prefijo':prefijo,'consecutivo':consecutivo
            })
            for wd in copied_payslip.worked_days_line_ids:
                wd.number_of_hours = -wd.number_of_hours
                wd.number_of_days = -wd.number_of_days
                wd.amount = -wd.amount
            for line in copied_payslip.line_ids:
                line.amount = -line.amount
            copied_payslips |= copied_payslip
        # formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        # treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return copied_payslip
        # {
        #     'name': ("Refund Payslip"),
        #     'view_mode': 'list, form',
        #     'view_id': False,
        #     'res_model': 'hr.payslip',
        #     'type': 'ir.actions.act_window',
        #     'target': 'current',
        #     'domain': [('id', 'in', copied_payslips.ids)],
        #     'views': [(treeview_ref and treeview_ref.id or False, 'list'), (formview_ref and formview_ref.id or False, 'form')],
        #     'context': {}
        # }
        
        
        # for payslip in self:
        #     numero_pred = payslip.prefijo+payslip.consecutivo
        #     fecha_gen_pred = payslip.FechaGen
        #     CUNEPred = payslip.cune
        #     if payslip.number:
        #         number = payslip.number
        #     else:
        #         number = payslip.number or self.env['ir.sequence'].next_by_code('salary.refund')
            
        #     numbersequence = self.env['ir.sequence'].search([('code', '=', 'salary.refund')])
        #     payslip.onchange_employee()
        #     prefijo = numbersequence.prefix
        #     longitudprefijo = len(prefijo)
        #     longitudsecuencia = len(number)
        #     consecutivo = number[longitudprefijo:longitudsecuencia]
        #     # delete old payslip lines
        #     payslip.line_ids.unlink()
        #     # set the list of contract for which the rules have to be applied
        #     # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
        #     contract_ids = payslip.contract_id.ids or \
        #         self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
        #     lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
        #     payslip.write({'line_ids': lines, 'number': number,'transaccionID':'',
        #                 'estado':'no_generada','nota_credito':tipo_nota,'causa':causa,
        #                 'CUNEPred':CUNEPred,'NumeroPred':numero_pred,'FechaGenPred':fecha_gen_pred,
        #                 'prefijo':prefijo,'consecutivo':consecutivo})

        # return True

    #@api.multi
    def refund_sheet(self):
        view_id = self.env.ref('electronicos_nomina.form_wizard_message2').id
        return {
			'name'     : "Ajuste de nomina",
			'type'     : 'ir.actions.act_window',
			'res_model': 'wk.wizard.message2',
			'view_mode': 'form',
            'view_id':view_id,
			'target'   : 'new',
			'res_id'   : False,
		}

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), datetime_time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), datetime_time.max)

            # compute leave days
            leaves = {}
            day_leave_intervals = contract.employee_id.iter_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            for day_intervals in day_leave_intervals:
                for interval in day_intervals:
                    holiday = interval[2]['leaves'].holiday_id
                    current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                        'name': holiday.holiday_status_id.name or _('Global Leaves'),
                        'sequence': 5,
                        'code': holiday.holiday_status_id.name or 'GLOBAL',
                        'number_of_days': 0.0,
                        'number_of_hours': 0.0,
                        'contract_id': contract.id,
                    })
                    leave_time = (interval[1] - interval[0]).seconds / 3600
                    current_leave_struct['number_of_hours'] += leave_time
                    work_hours = contract.employee_id.get_day_work_hours_count(interval[0].date(), calendar=contract.resource_calendar_id)
                    if work_hours:
                        current_leave_struct['number_of_days'] += leave_time / work_hours

            # compute worked days
            work_data = contract.employee_id.with_context(no_tz_convert=True).get_work_days_data(day_from, day_to, calendar=contract.resource_calendar_id)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }
            res.append(attendances) #"Cesantias",
            tipos = ["HED","HEN","HRN","HEDDF","HRDDF","HENDF","HRNDF",
            "VacacionesComunes","VacacionesCompensadas","Primas","Incapacidad_comun","Incapacidad100_comun","LicenciaMP","LicenciaR","LicenciaNR",
            "HuelgaLegal"]
            otros = ['ConceptoS','ConceptoNS',"AuxilioTransporte","ViaticoManuAlojS","ViaticoManuAlojNS","PagoS","PagoNS","PagoAlimentacionS","PagoAlimentacionNS",
            "Comision","PagoTercero","Anticipo","Dotacion","ApoyoSost","Teletrabajo","BonifRetiro","Indemnizacion","Reintegro"
            ,"BonificacionS","BonificacionNS","AuxilioS","AuxilioNS"]
            for tipo in tipos:
                attendances = {
                    'name': _(self.descripcion(tipo)),
                    'sequence': 1,
                    'code': tipo,
                    'number_of_days': 0,
                    'number_of_hours': 0,
                    'contract_id': contract.id,
                }
                res.append(attendances)
            res.extend(leaves.values())
        return res

    def descripcion(self,tipo):
        if tipo == "HED":
            return "Hora extra diurna"
        if tipo == "HEN":
            return "Hora Extra Nocturna"
        if tipo == "HRN":
            return "Hora Recargo Nocturno"
        if tipo == "HEDDF":
            return "Horas Extras Diurnas Dominical y Festivos"
        if tipo == "HENDF":
            return "Horas Extras Nocturna Dominical y Festivos"
        if tipo == "HRNDF":
            return "Horas Recargo Nocturna festiva dominical"
        if tipo == "HRDDF":
            return "Horas Recargo Diurno Dominical y Festivos"    
        if tipo == "VacacionesComunes":
            return "Vacaciones Comunes"
        if tipo == "VacacionesCompensadas":
            return "Vacaciones Compensadas"
        if tipo == "Primas":
            return "Primas"
        if tipo == "Incapacidad_comun":
            return "Incapacidad Comun 66 %"
        if tipo == "Incapacidad100_comun":
            return "Incapacidad Comun 100 %"
        if tipo == "LicenciaMP":
            return "Licencia de Maternidad o Paternidad"
        if tipo == "LicenciaR":
            return "Licencia Remunerada"
        if tipo == "LicenciaNR":
            return "Licencia NO Remunerada"
        if tipo == "HuelgaLegal":
            return "Huelga Legal"
        
        # if tipo == "OtroConcepto":
        #     return "Otros conceptos"
        
          
    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []

        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')

        otros = ['ConceptoS','ConceptoNS',"ViaticoManuAlojS","ViaticoManuAlojNS","PagoS","PagoNS","PagoAlimentacionS","PagoAlimentacionNS",
            "Comision","PagoTercero","Anticipo","Dotacion","ApoyoSost","Teletrabajo","BonifRetiro","Indemnizacion","Reintegro"
            ,"BonificacionS","BonificacionNS","AuxilioS","AuxilioNS","CompensacionO","CompensacionE","Sindicato","SancionPriv",
            "SancionPublic","Libranza","OtraDeduccion","PensionVoluntaria","RetencionFuente","AFC","Cooperativa","EmbargoFiscal",
            "PlanComplementarios","Educacion","Reintegro","Deuda","Cesantias","InteresesCesantias"]

        for contract in contracts:
            for otro in otros:
                input_data = {
                    'name': self.descripcion2(otro),
                    'code': otro,
                    'contract_id': contract.id,
                }
                res +=  [input_data]
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                }
                res += [input_data]
        return res

    def descripcion2(self,tipo):
        if tipo == "ConceptoS":
            return "Valor de los demás pagos fijos o variables realizados al trabajador (SALARIAL)"
        if tipo == "ConceptoNS":
            return "Valor de los demás pagos fijos o variables realizados al trabajador (NO SALARIAL)"
        if tipo == "ViaticoManuAlojS":
            return "Parte de los viáticos pagado al trabajador correspondientes a manutención y/o alojamiento.(SALARIAL)"
        if tipo == "ViaticoManuAlojNS":
            return "Parte de los viáticos pagado al trabajador correspondientes a manutención y/o alojamiento.(NO SALARIAL)"
        if tipo == "PagoS":
            return "Valor que el trabajador recibe como contraprestación por el trabajo realizado, por medio de bonos electrónicos, recargas, cheques, vales. es decir, todo pago realizado en un medio diferente a dinero en efectivo o consignación de cuenta bancaria (Salarial)."
        if tipo == "PagoNS":
            return "Valor que el trabajador recibe como contraprestación por el trabajo realizado, por medio de bonos electrónicos, recargas, cheques, vales. es decir, todo pago realizado en un medio diferente a dinero en efectivo o consignación de cuenta bancaria (NO Salarial)."
        if tipo == "PagoAlimentacionS":
            return "Valor que el trabajador recibe como concepto no salarial, por medio de bonos electrónicos, recargas, cheques, vales. es decir, todo pago realizado en un medio diferente a dinero en efectivo o consignación de cuenta bancaria (Para Alimentación Salarial)."    
        if tipo == "PagoAlimentacionNS":
            return "Valor que el trabajador recibe como concepto no salarial, por medio de bonos electrónicos, recargas, cheques, vales. es decir, todo pago realizado en un medio diferente a dinero en efectivo o consignación de cuenta bancaria (Para Alimentación NO Salarial)."
        if tipo == "Comision":
            return "Valor pagado al trabajador usualmente del área comercial, y de forma regular se liquida con un porcentaje sobre el importe de una operación, también se presenta como incentivo por el logro de objetivos."
        if tipo == "PagoTercero":
            return "Beneficios en cabeza del Trabjador que se pagan a un proveedor o tercero."
        if tipo == "Anticipo":
            return "Anticipos de Nómina."
        if tipo == "Dotacion":
            return "De conformidad con lo previsto en el artículo 230 del Código Sustantivo del Trabajo, o la norma que lo modifique, adicione o sustituya, corresponde al valor que el empleador dispone para suministrar la dotación de sus trabajadores."
        if tipo == "ApoyoSost":
            return "Corresponde al valor no salarial que el patrocinador paga de forma mensual como ayuda o apoyo economía al aprendiz o practicante universitario durante su etapa lectiva y fase practica."
        if tipo == "Teletrabajo":
            return "Valor que debe ser pagado al trabajador cuyo contrato indica expresamente que puede laborar mediante teletrabajo"
        if tipo == "BonifRetiro":
            return "Valor establecido por mutuo acuerdo por retiro del Trabajador"
        if tipo == "Indemnizacion":
            return "Valor de Indemnizacion establecido por ley"
        if tipo == "Reintegro":
            return "Valor que le regresa la empresa al trabajador por una deducción mal realizada en otro pago de nomina"
        if tipo == "BonificacionS":
            return "Son valores pagados al trabajador en forma de incentivo o recompensa por la contraprestación directa del servicio."
        if tipo == "BonificacionNS":
            return "Son valores de incentivos pagados al trabajador de forma ocasional y por mera liberalidad o los pactados entre las partes de forma expresa como pago no salarial."
        if tipo == "AuxilioS":
            return "Son beneficios, ayudas o apoyos económicos, pagados al trabajador de forma habitual o pactados entre las partes como factor salarial."
        if tipo == "AuxilioNS":
            return "Son beneficios, ayudas o apoyos económicos, pagados al trabajador de forma ocasional y por mera liberalidad o los pactados entre las partes de forma expresa como pago no salarial."
        if tipo == "CompensacionO":
            return "Compensacion Ordinaria"
        if tipo == "CompensacionE":
            return "Compensacion Extraordinaria"
        if tipo == "Sindicato":
            return "Las cuotas que los trabajadores sindicalizados deben aportar al sindicato al que estén afiliados, y siempre que medie autorización del empleado."
        if tipo == "SancionPriv":
            return "Valor por el del incumplimiento de una regla o norma de conducta obligatoria (Privada o Ordinaria)"
        if tipo == "SancionPublic":
            return "Valor por el del incumplimiento de una regla o norma de conducta obligatoria (Publica)"
        if tipo == "Libranza":
            return "Nombre de la Libranza que corresponda a las cuotas que el empleado deba pagar a una entidad financiera, para la amortización de un crédito que le haya sido otorgado por libranza"
        if tipo == "OtraDeduccion":
            return "Otro tipo de deducción dentro de la Nomina."
        if tipo == "PensionVoluntaria":
            return "Valor correspondiente al ahorro que hace el trabajador para complementar su pension obligatoria o cumplir metas especificas."
        if tipo == "RetencionFuente":
            return "Si hubiere lugar, la empresa deberá calcular y retener al empleado el valor correspondiente a retención en la fuente por ingresos laborales. Este valor será declarado y consignado en la respectiva declaración mensual de retención en la fuente."
        if tipo == "AFC":
            return "Corresponde a (Ahorro Fomento a la contruccion)"  
        if tipo == "Cooperativa":
            return "Las cuotas o aportes que los empleados hagan a las cooperativas legalmente constituidas"
        if tipo == "EmbargoFiscal":
            return "Los embargos ordenados por autoridad judicial competente contra los empleados deben ser descontados de la nómina por la empresa y consignarlos en la cuenta que el juez haya ordenado."
        if tipo == "PlanComplementarios":
            return "Valor de planes complementarios de salud al que el trabajador se encuentran afiliado, siempre que medie autorización del empleado."
        if tipo == "Educacion":
            return "Valor de servicios educativos que el trabajador autorice descuento."
        if tipo == "Reintegro":
            return "Valor que le regresa el trabajador a la empresa por un devengo mal realizado en otro pago de nómina"
        if tipo == "Deuda":
            return "Valor que se deba pagar por las obligaciones que el empleado tenga con su empresa, como puede ser un crédito que ésta le haya otorgado, o como compensación por algún perjuicio o detrimento económico que el empleado le haya causado a la empresa."    
        if tipo == "Cesantias":
            return "Pago de la Cesantia otorgada por Ley."    
        if tipo == "InteresesCesantias":
            return "Pago de los Intereses de Cesantia otorgada por Ley."    

    @api.onchange('employee_id')
    def on_change_employee(self):
        for record in self:
            generales = self.env['base_electronicos.tabla'].search([('name', '=', 'Nómina electrónica')])
            valores = generales.generales_id.search([('company_id', '=', self.employee_id.company_id.id)],limit=1)
            if not generales:
                return self.env['wk.wizard.message'].genrated_message("Error en el empleado ","Asignar una empresa al empleado","https://navegasoft.com")    
            print("IMPRIMIENDO valores")
            print(valores)
            if valores:
                self.prefijo = valores.prefijo
                self.consecutivo = valores.consecutivo
                self.paisgeneracion = valores.paisgeneracion
                self.departamentoestado = valores.departamentoestado
                self.municipiociudad = valores.municipiociudad
                self.Idioma = valores.Idioma
                self.ambiente = valores.ambiente
                self.tipoXML = valores.tipoXML
                self.PeriodoNomina = valores.PeriodoNomina
                ##Empleador
                self.RazonSocial = valores.RazonSocial
                self.PrimerApellido = valores.PrimerApellido
                self.SegundoApellido = valores.SegundoApellido
                self.PrimerNombre = valores.PrimerNombre
                self.OtrosNombres = valores.OtrosNombres
                self.NIT = valores.NIT
                self.DV = valores.DV
                self.PaisEmpleador = valores.PaisEmpleador
                self.MunicipioCiudadEmpleador = valores.MunicipioCiudadEmpleador
                self.DepartamentoEstadoEmpleador = valores.DepartamentoEstadoEmpleador
                self.DireccionEmpleador = valores.DireccionEmpleador
                self.id_plataforma = valores.id_plataforma
                self.password = valores.password
        #return
    # @api.model
    # def create(self, values):
        
        
    #     result = super(nomina_electronica, self).create(values) 
    #     print("IMPRIMIENDO valores despues")
    #     print(valores)
    #     return result   

    #@api.multi
    def action_cfdi_generate(self):
        urlini = "https://odoo15.navegasoft.com/admonclientes/status/"
        headers = {'content-type': 'application/json'}
        send = {"id_plataforma":self.id_plataforma,"transaccionID":self.transaccionID,"prefix":self.prefijo,"number":self.consecutivo,"ambiente":self.ambiente}
        result = requests.post(urlini,headers=headers,data = json.dumps(send))
        #resultado = json.loads(result.text)
        #print(result.text)
        if result.status_code == 200:
            resultado = json.loads(result.text)
            if "documentBase64" in resultado:
                final = resultado["documentBase64"]
                return self.env['wk.wizard.message'].genrated_message('Documento impreso', 'listos')
            else:
                if "error" in resultado:
                    final = resultado["error"]
                    final_error = json.loads(json.dumps(final))
                    data = final_error["data"]
                    data_final = data['message']
                    final_data = json.loads(json.dumps(data_final))
                    # archivo = final_data['code']
                    return self.env['wk.wizard.message'].genrated_message(data_final,"Los datos no estan correctos" ,"https://navegasoft.com")
                else:
                    final = json.loads(json.dumps(resultado))
                    final2 = final['result']
                    final_data = json.loads(json.dumps(final2)) #eval(final2)
                    #archivo = final_data['code']
                    # module_path = modules.get_module_path('tabla_nomina')        
                    # model = "facturas"
                    # if '\\' in module_path:
                    #     src_path = '\\static\\'
                    #     src_model_path = "{0}{1}\\".format('\\static', model)
                    # else:
                    #     src_path = '/static/'
                    #     src_model_path = "{0}{1}/".format('/static/', model)
                    
                    # if "model" folder does not exists create it
                    # os.chdir("{0}{1}".format(module_path, src_path))
                    # if not os.path.exists(model):
                    #     os.makedirs(model)
                    extension = ".pdf"
                    #file_path = "{0}{1}".format(module_path + src_model_path + str(name), extension)
                    #file_path = "{0}{1}".format(module_path + src_model_path + str(self.number), extension)
                    file_path = "/home/odoo/static/"+str(self.number)+extension
                    if not os.path.exists("/home/odoo/static/"):
                        os.makedirs("/home/odoo/static/")
                    if not (os.path.exists(file_path)):
                        size =1
                        if size == 0:
                            os.remove(file_path)
                            raise UserError(_('imprimible se esta preparando intenta de nuevo, Factura preparandose.'))
                        else:
                            import base64 
                            print(final_data)
                            if final_data['code'] == '400':
                                return self.env['wk.wizard.message'].genrated_message(final['mensaje'],final['titulo'] ,final['link'])
                                #self.env['wk.wizard.message'].genrated_message('Estamos recibiendo un codigo 400 Es necesario esperar para volver imprimir el documento', 'Es necesario esperar para volver a imprimir el documento')
                            elif final_data['code'] == '200':
                                print("el codigo")
                                print(final_data['code'])
                                image_64_encode = base64.b64decode(final_data['documentBase64']) #eval(
                                i64 = base64.b64encode(image_64_encode)
                                att_id = self.env['ir.attachment'].create({
                                    'name': self.number+extension,
                                    'type': 'binary',
                                    'datas': i64,
                                    #'datas_fname': self.number+extension,
                                    'res_model': 'hr.payslip',
                                    'res_id': self.id,
                                    })
                                if att_id:
                                    # self.write({"impreso":True})
                                    return self.env['wk.wizard.message'].genrated_message("Ve a attachment","Factura impresa" ,"https://navegasoft.com")
                            else:
                                print(final_data)
                                return self.env['wk.wizard.message'].genrated_message(final_data['mensaje'],final_data['titulo'] ,final_data['link'])
                                #self.env['wk.wizard.message'].genrated_message('Estamos recibiendo un codigo de error Es necesario esperar para volver imprimir el documento', 'Es necesario esperar para volver a imprimir el documento')
                                
                    else:
                        raise UserError(_('Ve a attachment, Factura ya impresa.'))
 
                    final = resultado["error"]
                    final_error = json.loads(json.dumps(final))
                    data = final_error["data"]
                    data_final = data['message']      
        else:
            raise Warning(result)
        
        
    #@api.multi
    def genera_cufe(self):
        urlini = "https://odoo15.navegasoft.com/admonclientes/cune/"
        headers = {'content-type': 'application/json'}
        send = {"id_plataforma":self.id_plataforma,"transaccionID":self.transaccionID,"prefix":self.prefijo,"number":self.consecutivo,"ambiente":self.ambiente}
        result = requests.post(urlini,headers=headers,data = json.dumps(send))
        #resultado = json.loads(result.text)
        #print(result.text)
        print(result)
        if result.status_code == 200:
            resultado = json.loads(result.text)
            print("el primer resultado es !!!")
            print(resultado)
            if "cune" in resultado:
                final = resultado["cune"]
                return self.env['wk.wizard.message'].genrated_message('CUNE: '+final, 'listos')
            else:
                if "error" in resultado:
                    final = resultado["error"]
                    final_error = json.loads(json.dumps(final))
                    data = final_error["data"]
                    data_final = data['message']
                    final_data = json.loads(json.dumps(data_final))
                    # archivo = final_data['code']
                    return self.env['wk.wizard.message'].genrated_message(data_final,"Los datos no estan correctos" ,"https://navegasoft.com")
                else:
                    final = json.loads(json.dumps(resultado))
                    final2 = final['result']
                    final_data = json.loads(json.dumps(final2)) #eval(final2)
                    print('y el resultado es ...')
                    print(final_data)
                    if 'CUNE' in final_data:
                        self.write({"cune":final_data['CUNE']})
                        return self.env['wk.wizard.message'].genrated_message("Este es el CUNE "+final_data['CUNE'],"Se guardo dentro de los datos de la nomina" ,"https://navegasoft.com")
                    else:
                        return self.env['wk.wizard.message'].genrated_message('Estamos recibiendo un codigo de error Es necesario esperar para volver generar el cune', 'Es necesario esperar para volver a imprimir el documento')
                    final = resultado["error"]
                    final_error = json.loads(json.dumps(final))
                    data = final_error["data"]
                    data_final = data['message']      
        else:
            raise Warning(result)

    #@api.multi
    def envio_directo(self):
        import time
        now2 = datetime.now()
        current_time = now2.strftime("%H:%M:%S")
        self.on_change_employee()
        if self.credit_note == True:
            numeracion = self.env['ir.sequence'].search([('code', '=', 'salary.refund')])
            lon_prefix = len(numeracion.prefix)
            long_total = len(self.number)
            number = self.number[lon_prefix:long_total]
            self.prefijo = numeracion.prefix
            self.consecutivo = number
        else:
            print("la compañia del empleado")
            print(self.employee_id.company_id.id)
            #,('company_id', '=', self.employee_id.company_id.id)
            numeracion = self.env['ir.sequence'].sudo().search([('code', '=', 'salary.slip')],limit=1)
            print("la numeracion del empleado es")
            print(numeracion.company_id)
            lon_prefix = len(numeracion.prefix)
            long_total = len(self.number)
            number = self.number[lon_prefix:long_total]
            self.prefijo = numeracion.prefix
            self.consecutivo = number
        self.FechaGen = str(now2.date())
        self.HoraGen = str(current_time)
        urlini = "https://odoo15.navegasoft.com/admonclientes/objects/"
        valores = self.env['base_electronicos.tabla'].search([('name', '=', 'Nómina electrónica')])
        
        response2={}
        valores_lineas = valores.mp_id
        send = {}
        for linea in valores_lineas:
            if linea.codigo:
                if linea.dias == True:
                    for lineacomprobante in self.worked_days_line_ids:
                        if linea.codigo == lineacomprobante.code:
                            if lineacomprobante.number_of_days > 0.0:
                                send[linea.name] = lineacomprobante.number_of_days
                elif linea.horas == True:
                    for lineacomprobante in self.worked_days_line_ids:
                        if linea.codigo == lineacomprobante.code:
                            if lineacomprobante.number_of_hours > 0.0:
                                send[linea.name] = lineacomprobante.number_of_hours
                elif linea.porcentaje == True:
                    reglas = self.env['hr.salary.rule'].search([('code','=',linea.codigo)])
                    for regla in reglas:
                        if regla.porcentaje:
                            send[linea.name] = regla.porcentaje
                else:
                    for lineacomprobante in self.line_ids:
                        if linea.codigo == lineacomprobante.code:
                            if lineacomprobante.amount != 0.00:
                                send[linea.name] = lineacomprobante.amount
            elif linea.campo_tecnico:
                #buscar en el comprobante el codigo
                try:
                    #search de company_id in the field
                    if linea.campo_tecnico:
                        if "self.employee_id.address_home_id.state_id.code[0:2]" == linea.campo_tecnico:
                            if self.employee_id.address_home_id.state_id.code:
                                send[linea.name] = eval(linea.campo_tecnico)
                            else:
                                self.write({"estado":"Generada_con_errores","error":"El campo esta vacio "+linea.campo_tecnico})
                                return self.env['wk.wizard.message'].genrated_message("El campo esta vacio "+linea.campo_tecnico,"Error en el campo"+linea.name,"https://navegasoft.com")    
                        else:
                            if eval(linea.campo_tecnico):
                                send[linea.name] = eval(linea.campo_tecnico)
                            # else:
                                # if linea.obligatorio:
                                #     self.write({"estado":"Generada_con_errores","error":"El campo esta vacio "+linea.campo_tecnico})
                                #     return self.env['wk.wizard.message'].genrated_message("El campo esta vacio "+linea.campo_tecnico,"Error en el campo"+linea.name,"https://navegasoft.com")    
                except SyntaxError:
                    self.write({"estado":"Generada_con_errores","error":"El campo esta vacio "+linea.campo_tecnico})
                    return self.env['wk.wizard.message'].genrated_message("El campo esta vacio "+linea.campo_tecnico,"Error en el campo"+linea.name,"https://navegasoft.com")
                    #pass
                # if linea.name == "DepartamentoEstado":
                #     print(linea.name)
                #     print(linea.campo_tecnico)
                #     print(eval(linea.campo_tecnico))
            # else:
            #     send[linea.name] = None
        # print(send)
        #send['credit_note']= self.credit_note
        headers = {'content-type': 'application/json'}
        result = requests.post(urlini,headers=headers,data = json.dumps(send))
        if result.status_code == 200:
            resultado = json.loads(result.text)
            print("resultado")
            print(resultado)
            if "result" in resultado:
                final = resultado["result"]
                print("final")
                print(final)
                if "error_d" in final:
                    if "transactionID" in final:
                        self.write({"impreso":False,"transaccionID":final['transactionID'],"estado":"Generada_correctamente","error":""})
                    else:
                        self.write({"estado":"Generada_con_errores","error":final['mensaje'],"solucion":final['link']})
                        return self.env['wk.wizard.message'].genrated_message(final['mensaje'],final['titulo'] ,final['link'])
                else:
                    final_error = json.loads(final) #.decode("utf-8")
                    final_text = final_error['error']
                    self.write({"estado":"Generada_con_errores","error":final_text['mensaje'],"solucion":final_text['link']})
                    return self.env['wk.wizard.message'].genrated_message(final_text['mensaje'], final_text['titulo'],final_text['link'])
                # else:
                #     return self.env['wk.wizard.message'].genrated_message('3 No hemos recibido una respuesta satisfactoria vuelve a enviarlo', 'Reenviar')    
            else:
                if "error" in resultado:
                    final = resultado["error"]
                    final_error = json.loads(json.dumps(final))
                    data = final_error["data"]
                    data_final = data['message']
                    print("data_final")
                    print(final)
                    self.write({"estado":"Generada_con_errores","error":data_final,"solucion":"Proximamente video de solucion"})
                    return self.env['wk.wizard.message'].genrated_message(data_final,"Los datos no estan correctos" ,"https://navegasoft.com")
        else:
            self.write({"estado":"Generada_con_errores","error":result,"solucion":"Volver a enviar el comprobante"})
            raise Warning(result)
            return self.env['wk.wizard.message'].genrated_message('Existen problemas de coneccion debes reportarlo con navegasoft', 'Servidor')


    def generate_multiple_payroll(self):
        for record in self._context.get('active_ids'):
            if record:
                payslip = self.env[self._context.get('active_model')].browse(record)
                payslip.envio_directo()


class nomina_hr_contract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    auxilio_de_transporte = fields.Float("Auxilio de transporte")
    uvt =  fields.Float("UVT")
    salario_minimo = fields.Float("Salario Minimo")
    tipo_contrato = fields.Selection([
        ('1', 'Término Fijo'),
        ('2', 'Término Indefinido'),
        ('3', 'Obra o Labor'),
        ('4', 'Aprendizaje'),
        ('5', 'Practicas'),
    ], string='Tipo Contrato')
    
    tipo_trabajador = fields.Selection([
        ('01', 'Dependiente'),
        ('02', 'Servicio domestico'),
        ('03', 'Independiente'),
        ('04', 'Madre comunitaria'),
        ('12', 'Aprendices del Sena en etapa lectiva'),
        ('16', 'Independiente agremiado o asociado'),
        ('18', 'Funcionarios públicos sin tope máximo de ibc'),
        ('19', 'Aprendices del SENA en etapa productiva'),
        ('20', 'Estudiantes (régimen especial ley 789 de 2002)'),
        ('21', 'Estudiantes de postgrado en salud'),
        ('22', 'Profesor de establecimiento particular'),
        ('23', 'Estudiantes aportes solo riesgos laborales'),
        ('30', 'Dependiente entidades o universidades públicas con régimen especial en salud'),
        ('31', 'Cooperados o pre cooperativas de trabajo asociado'),
        ('32', 'Cotizante miembro de la carrera diplomática o consular de un país extranjero o funcionario de organismo multilateral'),
        ('33', 'Beneficiario del fondo de solidaridad pensional'),
        ('34', 'Concejal municipal o distrital o edil de junta administrativa local que percibe honorarios amparado por póliza de salud'),
        ('35', 'Concejal municipal o distrital que percibe honorarios no amparado con póliza de salud'),
        ('36', 'Concejal municipal o distrital que percibe honorarios no amparado con póliza de salud beneficiario del fondo de solidaridad pensional'),
        ('40', 'Beneficiario upc adicional'),
        ('41', 'Beneficiario sin ingresos con pago por tercero'),
        ('42', 'Cotizante pago solo salud articulo 2 ley 1250 de 2008 (independientes de bajos ingresos)'),
        ('43', 'Cotizante voluntario a pensiones con pago por tercero'),
        ('44', 'Cotizante dependiente de empleo de emergencia con duración mayor o igual a un mes'),
        ('45', 'Cotizante dependiente de empleo de emergencia con duración menor a un mes'),
        ('47', 'Trabajador dependiente de entidad beneficiaria del sistema general de participaciones - aportes patronales'),
        ('51', 'Trabajador de tiempo parcial'),
        ('52', 'Beneficiario del mecanismo de protección al cesante'),
        ('53', 'Afiliado participe'),
        ('54', 'Pre pensionado de entidad en liquidación.'),
        ('55', 'Afiliado participe - dependiente'),
        ('56', 'Pre pensionado con aporte voluntario a salud'),
        ('57', 'Independiente voluntario al sistema de riesgos laborales'),
        ('58', 'Estudiantes de prácticas laborales en el sector público'),
        ('59', 'Independiente con contrato de prestación de servicios superior a 1 mes'),
        ('61', 'Beneficiario programa de reincorporación'),
        ], string='Tipo Trabajador')
    sub_tipo_trabajador = fields.Selection([
        ('00', 'No Aplica'),
        ('01', 'Dependiente pensionado por vejez activo'),
        # ('02', 'Independiente pensionado por vejez activo'),
        # ('03', 'Cotizante no obligado a cotizar a pensión por edad'),
        # ('04', 'Cotizante con requisitos cumplidos para pensión'),
        # ('12', 'Cotizante a quien se le ha reconocido indemnización sustitutiva o devolución de saldos'),
        # ('16', 'Cotizante perteneciente a un régimen de exceptuado de pensiones a entidades autorizadas para recibir aportes exclusivamente de un grupo de sus propios'),
        # ('18', 'Cotizante pensionado con mesada superior a 25 smlmv'),
        # ('19', 'Residente en el exterior afiliado voluntario al sistema general de pensiones y/o afiliado'),
        # ('20', 'Conductores del servicio público de transporte terrestre automotor individual de pasajeros en vehículos taxi decreto 1047 de 2014'),
        # ('21', 'Conductores servicio taxi no aporte pensión dec. 1047'),
        ], string='Subtipo de Trabajador')
    AltoRiegoPension = fields.Selection([
        ('false', 'NO'),
        ('true', 'SI'),
        ], string='Alto Riego Pension',default='false')
    SalarioIntegral = fields.Selection([
        ('false', 'NO'),
        ('true', 'SI'),
        ], string='Salario Integral',default='false')
    banco = fields.Char("Banco")
    tipo_cuenta = fields.Char("Tipo cuenta")
    numero_cuenta = fields.Char("Numero de cuenta")
    metodo_pago = fields.Selection([
        ('1', 'Instrumento no definido'),
        ('2', 'Crédito ACH'),
        ('3', 'Débito ACH'),
        ('4', 'Reversión débito de demanda ACH'),
        ('5', 'Reversión crédito de demanda ACH'),
        ('6', 'Crédito de demanda ACH'),
        ('7', 'Débito de demanda ACH'),
        ('8', 'Mantener'),
        ('9', 'Clearing Nacional o Regional'),
        ('10', 'Efectivo'),
        ('11', 'Reversión Crédito Ahorro'),
        ('12', 'Reversión Débito Ahorro'),
        ('13', 'Crédito Ahorro'),
        ('14', 'Débito Ahorro'),
        ('15', 'Bookentry Crédito'),
        ('16', 'Bookentry Débito'),
        ('17', 'Concentración de la demanda en efectivo Desembolso Crédito (CCD)'),
        ('18', 'Concentración de la demanda en efectivo Desembolso (CCD) débito'),
        ('19', 'Crédito Pago negocio corporativo (CTP)'),
        ('20', 'Cheque'),
        ('21', 'Proyecto bancario'),
        ('22', 'Proyecto bancario certificado'),
        ('23', 'Cheque bancario'),
        ('24', 'Nota cambiaria esperando aceptación'),
        ('25', 'Cheque certificado'),
        ('26', 'Cheque Local'),
        ('27', 'Débito Pago Negocio Corporativo (CTP)'),
        ('28', 'Crédito Negocio Intercambio Corporativo (CTX)'),
        ('29', 'Débito Negocio Intercambio Corporativo (CTX)'),
        ('30', 'Transferencia Crédito'),
        ('31', 'Transferencia Débito'),
        ('32', 'Concentración Efectivo / Desembolso Crédito plus (CCD+)'),
        ('33', 'Concentración Efectivo / Desembolso Débito plus (CCD+)'),
        ('34', 'Pago y depósito pre acordado (PPD)'),
        ('35', 'Concentración efectivo ahorros / Desembolso Crédito (CCD)'),
        ('36', 'Concentración efectivo ahorros / Desembolso Crédito (CCD)'),
        ('37', 'Pago Negocio Corporativo Ahorros Crédito (CTP)'),
        ('38', 'Pago Negocio Corporativo Ahorros Débito	(CTP)'),
        ('39', 'Crédito Negocio Intercambio Corporativo (CTX)'),
        ('40', 'Débito Negocio Intercambio Corporativo (CTX)'),
        ('41', 'Concentración efectivo/Desembolso Crédito plus (CCD+)'),
        ('42', 'Consignación bancaria'),
        ('43', 'Concentración efectivo / Desembolso Débito plus (CCD+)'),
        ('44', 'Nota cambiaria'),
        ('45', 'Transferencia Crédito Bancario'),
        ('46', 'Transferencia Débito Interbancario'),
        ('47', 'Transferencia Débito Bancaria'),
        ('48', 'Tarjeta Crédito'),
        ('49', 'Tarjeta Débito'),
        ('50', 'Postgiro'),			
        ('51', 'Telex estándar bancario francés'),
        ('52', 'Pago comercial urgente'),
        ('53', 'Pago Tesorería Urgente'),
        ('60', 'Nota promisoria'),
        ('61', 'Nota promisoria firmada por el acreedor'),
        ('62', 'Nota promisoria firmada por el acreedor, avalada por el banco'),
        ('63', 'Nota promisoria firmada por el acreedor, avalada por un tercero'),
        ('64', 'Nota promisoria firmada por el banco'),
        ('65', 'Nota promisoria firmada por un banco avalada por otro banco'),
        ('66', 'Nota promisoria firmada'),
        ('67', 'Nota promisoria firmada por un tercero avalada por un banco'),
        ('70', 'Retiro de nota por el por el acreedor'),
        ('71', 'Bonos'),
        ('72', 'Vales'),
        ('74', 'Retiro de nota por el por el acreedor sobre un banco'),
        ('75', 'Retiro de nota por el acreedor, avalada por otro banco'),
        ('76', 'Retiro de nota por el acreedor, sobre un banco avalada por un tercero'),
        ('77', 'Retiro de una nota por el acreedor sobre un tercero'),
        ('78', 'Retiro de una nota por el acreedor sobre un tercero avalada por un banco'),
        ('91', 'Nota bancaria transferible'),
        ('92', 'Cheque local trasferible'),
        ('93', 'Giro referenciado'),
        ('94', 'Giro urgente'),
        ('95', 'Giro formato abierto'),
        ('96', 'Método de pago solicitado no usado'),
        ('97', 'Clearing entre partners'),
        ('ZZZ', 'Acuerdo mutuo'),
        ], string='Metodo de pago',default='10') 

# class electronicos_nomina(models.Model):
#     _name = 'electronicos_nomina.electronicos_nomina'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100