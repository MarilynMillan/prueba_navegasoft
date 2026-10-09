from odoo import models, fields, modules,tools , api,_ 
import os
import requests
import json 
from odoo.exceptions import AccessError, UserError,  ValidationError
import babel
from odoo.tools.safe_eval import safe_eval

import time
from dateutil import relativedelta
from datetime import datetime, timedelta
from datetime import time as datetime_time


class nomina_electronica(models.Model):
    _name = 'consolidated.payroll.slip'
    _inherit = 'consolidated.payroll.slip'

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
    #     readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})

    credit_note = fields.Boolean(
        string='Credit Note', readonly=True,
        #states={'draft': [('readonly', False)], 'verify': [('readonly', False)]},
        help="Indicates this payslip has a refund of another")

    #@api.onchange('employee_id')
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
                                    'res_model': 'consolidated.payroll.slip',
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
            if "result" in resultado:
                final = resultado["result"]
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

    def generate_multiple_consolidated(self):
        for record in self._context.get('active_ids'):
            payslip = self.env[self._context.get('active_model')].browse(record)
            payslip.envio_directo()

class MultipleConsolidatedGenerate(models.TransientModel):
    _name = "multiple.consolidated.payroll"
    _description = "generate Multiple Consolidated Payroll"

    def generate_multiple_consolidated(self):
        for record in self._context.get('active_ids'):
            payslip = self.env[self._context.get('active_model')].browse(record)
            payslip.envio_directo()
           