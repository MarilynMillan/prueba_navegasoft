# -*- coding: utf-8 -*-
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, timedelta
from odoo.http import request, route, content_disposition,Response
from odoo import fields,exceptions, _
import base64
import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64

_logger = logging.getLogger(__name__)

class Employee_page(CustomerPortal):
    """clase con herencia múltiple, encargada de enrutar los puntos finales segun la escucha y funcionamiento del
    portal """

    def get_payroll_certificates(self):
        """Obtener nonimas de empleado

        Returns:
            list
        """
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)])
        # print("employee")
        # print(employee)
        hr_payroll = request.env['hr.payslip'].sudo()
        domain = [('employee_id', '=', employee.id), ('state', '=', 'done')]
        
        payroll_list = hr_payroll.search(domain)
        # print("payroll_list")
        # print(payroll_list)   

        if len(payroll_list) > 1:
            payroll_list = sorted(payroll_list, key=lambda i: i['id'], reverse=True)
        
        def iter_payroll_list(pay):
            date_f = str(pay.date_from).split("-")
            date_t = str(pay.date_to).split("-")
            
            date_from = datetime(int(date_f[0]), int(date_f[1]), int(date_f[2])).strftime("%d, %B del %y")
            date_to = datetime(int(date_t[0]), int(date_t[1]), int(date_t[2])).strftime("%d, %B del %y")
        
            return {
                'id': pay.id,
                'number': pay.number,
                'name': pay.name,
                'date_from': date_from,
                'date_to': date_to
            }
            
        payroll_list = list(map(iter_payroll_list, payroll_list))
        
        return payroll_list

    def get_my_leaves(self):
        """Obtener ausencias del usuario

        Returns:
            list
        """
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)])
        
        hr_leave = request.env['hr.leave'].sudo()
        domain = [('employee_id', '=', employee.id)]
        leaves = hr_leave.search(domain)
            
        return leaves
    
    @route('/certificate/income', methods=['POST', 'GET'], csrf=False, type='http', auth="user", website=True)
    def print_certificate_income(self, **kw):
        """Método que permite imprimir el certificado de ingresos y retenciones desde el portal
        @param kw:
        @return: request.make_response(pdf, headers=pdfhttpheaders)
        """
        if not request.params.get('year'):
            raise exceptions.ValidationError("El año es requerido")
        
        user_auth = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_auth.id)])
        year = int(request.params['year'])
        certificate_content_disposition = content_disposition(f"{_('Income Withholding')}.pdf")
        
        iw_report = request.env['income.withholding.report']
        iw_report.sudo().create(
            {'company_id': employee.company_id.id, 'employee_id': employee.id, 'certificate_year': year})

        data = {
            'ids': iw_report.ids,
            'model': iw_report._name,
            'form': {
                'company_id': employee.company_id.id,
                'employee_id': employee.id,
                'certificate_year': year
            }
        }

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('employee_reports_portal.action_report_income_withholding_certification', 
                                                                       res_ids=iw_report.id, data=data)[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), 
            ('Content-Length', len(pdf)),
            ('Content-Disposition', certificate_content_disposition),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @route('/certificates', methods=['POST', 'GET'], csrf=False, type='http', auth="user", website=True)
    def print_certificates(self, **kw):
        """Imprimir certificados laborales"""
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)])
        contract = list(employee.current_contract)
        certificate_type = int(request.params.get('type', 1))
        
        certificate_template = 'action_report_laboral_certification'
        certificate_content_disposition = content_disposition(f"{_('Labor Certificate')}.pdf")
        if certificate_type == 2:
            certificate_template = 'action_report_laboral_certification_salary'
            certificate_content_disposition = content_disposition(f"{_('Labor Certificate With Salary')}.pdf")
            
        elif certificate_type == 3:
            certificate_template = 'action_report_laboral_certification_fn'
            certificate_content_disposition = content_disposition(f"{_('Labor Certificate With Functions')}.pdf")
            
        elif certificate_type == 4:
            certificate_template = 'action_report_laboral_certification_fn_salary'
            certificate_content_disposition = content_disposition(f"{_('Labor Certificate With Functions And Salary')}.pdf")
        
        elif certificate_type == 5:
            certificate_template = 'action_report_laboral_certification_fn_salary_variable'
            certificate_content_disposition = content_disposition(f"{_('Labor Certificate With Functions And Salary Variable')}.pdf")

        if contract:
            pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(f"employee_reports_portal.{certificate_template}", [employee.id])[0]
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'), 
                ('Content-Length', len(pdf)),
                ('Content-Disposition', certificate_content_disposition),
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.render("employee_reports_portal.portal_not_found_certificate")
        
    @route('/certificate/payslip', methods=['POST', 'GET'], csrf=False, type='http', auth="user", website=True)
    def print_certificate_payslip(self, **kw):
        """
        Método que permite imprimir el reporte de nomina de un empleado.
        @param kw:
        @return: request.make_response(pdf, headers=pdfhttpheaders)
        """
        if not request.params.get('payroll_id'):
            raise exceptions.ValidationError("El recibo de nómina es requerido")
        
        payroll = int(request.params['payroll_id'])
        certificate_content_disposition = content_disposition(f"{_('Payslip')}.pdf")
        
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf("hr_payroll.action_report_payslip", payroll)[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), 
            ('Content-Length', len(pdf)),
            ('Content-Disposition', certificate_content_disposition)
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @route('/get_condicion', methods=['POST', 'GET'], type='json', csrf=False, auth="public", website=True)
    def get_condicion(self, **kw):
        argumento = request.params.get('tipos_input')
        if not argumento:
            raise exceptions.ValidationError("ajax no funcionando")
        condicion = request.env['hr.leave.type'].sudo().search([('id','=',argumento)],limit=1 )
        return condicion.condicion,condicion.tratamiento_datos
    
    


    @http.route('/save_leave', methods=['POST'], type='http', auth="user", website=True, csrf=True)
    def save_leave(self, **post):
        def normalize_hour_string(hour_str):
            if ':' not in hour_str:
                return f"{hour_str.zfill(2)}:00"
            return hour_str
        try:
            # Leer valores del formulario
            holiday_status_id = post.get('holiday_status_id')
            name = post.get('name')
            date_from = post.get('request_date_from')
            date_to = post.get('request_date_to')
            tratamiento_raw = post.get('tratamiento_datos', 'NO')
            request_unit_hours = post.get('request_unit_hours') == 'SI'
            request_hour_from_str = normalize_hour_string(post.get('request_hour_from', '00:00'))
            request_hour_to_str = normalize_hour_string(post.get('request_hour_to', '00:00'))

            request_hour_from = datetime.strptime(request_hour_from_str, '%H:%M').time()
            request_hour_to = datetime.strptime(request_hour_to_str, '%H:%M').time()
            
            # Validaciones básicas
            if not holiday_status_id or not date_from or not date_to:
                raise ValidationError("Debe completar todos los campos obligatorios.")

            if tratamiento_raw not in ['SI', 'NO']:
                raise ValidationError("Valor inválido para tratamiento de datos.")

            tratamiento = tratamiento_raw == 'SI'

            # Validar fechas
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            dt_to = datetime.strptime(date_to, '%Y-%m-%d')
            today = datetime.today()
            max_date = today + timedelta(days=730)

            if dt_from > max_date or dt_to > max_date:
                raise ValidationError("La fecha no puede ser mayor a dos años a partir de hoy.")

            # Buscar empleado y tipo de ausencia
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
            tipo = request.env['hr.leave.type'].sudo().browse(int(holiday_status_id))

            if tipo.obligar_adjunto:
                file = request.httprequest.files.get('attachment')
                if not file:
                    raise ValidationError("Debe adjuntar un archivo para este tipo de ausencia.")

            # Calcular duración
            if request_unit_hours:
                unidad = 'Hours'
                
                # Convertir las horas a datetime con una fecha dummy
                dt_from_hour = datetime.combine(datetime.today(), request_hour_from)
                dt_to_hour = datetime.combine(datetime.today(), request_hour_to)
            
                if dt_to_hour < dt_from_hour:
                    # Caso de cruce de medianoche (ej. 23:00 -> 08:00 del siguiente día)
                    dt_to_hour += timedelta(days=1)
            
                horas_diferencia = (dt_to_hour - dt_from_hour).total_seconds() / 3600.0  # en horas
                dias = horas_diferencia / 8.0
                horas = horas_diferencia
            else:
                unidad = 'Days'
                dias = (dt_to - dt_from).days + 1
                horas = dias * 8
            
            # Crear ausencia
            leave = request.env['hr.leave'].sudo().create({
                'holiday_status_id': int(holiday_status_id),
                'name': name,
                'request_date_from': date_from,
                'request_date_to': date_to,
                'date_from': date_from,
                'date_to': date_to,
                'leave_type_request_unit': unidad,
                'request_unit_hours': request_unit_hours,
                'request_hour_from': request_hour_from.hour,
                'request_hour_to': request_hour_to.hour,
                #'number_of_days_display': horas,
                'number_of_days': dias,
                'tratamiento_datos': tratamiento,
                'employee_id': employee.id,
            })

            # Procesar adjunto
            file = request.httprequest.files.get('attachment')
            if file:
                attachment_data = base64.b64encode(file.read())
                request.env['ir.attachment'].sudo().create({
                    'name': file.filename,
                    'type': 'binary',
                    'datas': attachment_data,
                    'res_model': 'hr.leave',
                    'res_id': leave.id,
                })

            return request.redirect('/my/home')

        except Exception as e:
            # Puedes redirigir con mensaje de error si tienes un template específico
           return request.render('employee_reports_portal.hr_leave_error', {
        'error_message': str(e),
    })


    #@route('/save_leave', methods=['POST', 'GET'], type='json', csrf=False, auth="public", website=True)
    #def save_leave(self, **kw):
    #    # print("entro controler")
    #    diccionario = request.params.get('diccionario')
    #    file = request.params.get('file')
    #    # print("consiguio diccionario")
    #    # print(diccionario)
    #    print("tratamiento")
    #    print(diccionario['tratamiento_datos'])
    #    if diccionario['tratamiento_datos']:
    #        tratamiento = True
    #    else:
    #        tratamiento = False
    #    
    #    print(tratamiento)
    #    if not diccionario:
    #        raise exceptions.ValidationError("ajax no funcionando")
    #    # print("haber que paso")
    #    user_auth = request.env.user
    #    employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_auth.id)])
    #    print("diccionario['holiday_status_id']")
    #    print(diccionario['request_date_from'])
    #    if diccionario['holiday_status_id'] == "":
    #        raise exceptions.ValidationError("Debe seleccionar un tipo de ausencia")
    #    if diccionario['request_date_from'] == "":
    #        raise exceptions.ValidationError("Debe seleccionar una fecha de inicio")
    #    if diccionario['request_date_to'] == "":
    #        raise exceptions.ValidationError("Debe seleccionar una fecha de finalización")
    #    
    #    tipo = request.env['hr.leave.type'].sudo().search([('id', '=', diccionario['holiday_status_id'])])
    #    # respuesta = request.env['hr.leave.type'].check_date2(employee.id)
    #    if tipo.obligar_adjunto == True:
    #        if not file:
    #            raise exceptions.ValidationError("Debe adjuntar un archivo")
    #    #2023-08-04T13:30    
#
    #    print(diccionario['request_date_to'])
    #    
    #    dt = datetime.strptime(diccionario['request_date_to'], '%Y-%m-%d')
    #    dt2 = datetime.strptime(diccionario['request_date_from'], '%Y-%m-%d')
#
    #    # Obtener la fecha actual
    #    fecha_actual = datetime.now()
#
    #    # Calcular la fecha que será dos años a partir de ahora
    #    fecha_dos_anos_adelante = fecha_actual + timedelta(days=730)  # 365 días * 2 años
#
    #    # Comparar las fechas
    #    if dt > fecha_dos_anos_adelante:
    #        raise ValueError("La fecha no puede ser mayor a dos años a partir de la fecha actual.")
    #    if dt2 > fecha_dos_anos_adelante:
    #        raise ValueError("La fecha no puede ser mayor a dos años a partir de la fecha actual.")
    #    
    #    # dt = timezone('UTC').localize(dt)
    #    # dt2 = timezone('UTC').localize(dt2)
    #    print("diccionario 00000000000000000000")
    #    print(diccionario['request_unit_hours'])
    #    print(type(diccionario['request_unit_hours']))
    #    if diccionario['request_unit_hours']:
    #        print("horaS de diferencia")
    #        request_unit_hours = "Hours"
    #        horasodias = diccionario['number_of_days_display']
    #        dias =horasodias/8
    #    else:
    #        print("dias de diferencia")
    #        print(dt.day-dt2.day+1)
    #        request_unit_hours = "Days"
    #        horasodias = dt.day-dt2.day+1*8
    #        dias = dt.day-dt2.day+1
#
    #    nuevodiccionario = {
    #        "holiday_status_id":tipo.id,
    #        "request_date_from":diccionario['request_date_from'],
    #        "request_date_to":diccionario['request_date_to'],	
    #        "date_from":diccionario['request_date_from'],
    #        "date_to":diccionario['request_date_to'],	
    #        "name":diccionario['name'],
    #        "leave_type_request_unit":request_unit_hours,
    #        "request_unit_hours":diccionario['request_unit_hours'],
    #        "request_hour_from":diccionario['request_hour_from'],
    #        "request_hour_to":diccionario['request_hour_to'],
    #        "number_of_days_display":horasodias,
    #        "number_of_days": dias,
    #        "tratamiento_datos":tratamiento,
    #        'employee_id': employee.id,
    #    }
    #    # print(nuevodiccionario)
    #    print(nuevodiccionario)
    #    condicion = request.env['hr.leave'].sudo().create(nuevodiccionario)
    #    if file:
    #        base64 = file
    #        # article_1 = unicodedata.normalize('NFKD', article).encode('ascii', 'ignore')
    #        # article_2 = article_1.lstrip('data:image/jpeg;base64,')
    #        print(request.params.get('nombre_file'))
    #        attach = file.strip('data:application/pdf;base64').strip('data:image/jpg;base64').strip('data:image/png;base64').strip('data:image/jpeg;base64')
    #        Attachments = request.env['ir.attachment']
    #        attachment = Attachments.sudo().create({
    #            'name': request.params.get('nombre_file'),
    #            'type': 'binary',
    #            'res_model':'hr.leave',
    #            'res_id': condicion.id,
    #            'datas': attach,
    #        })
    #    # print("como que no paso")
    #    
    #    return request.redirect('/my/home')

    @route(['/my', '/my/home'], type='http', auth="user", website=True, override=True)
    def home(self, **kw):
        """
        Método que hace una sobrecarga del método home en la clase CustomerPortal
        @param kw:
        @return:
        recordar que tengo unas variables que se usan para el modulo requerimiento_personal
        """
        _logger.info("employees++++++++++++++++++++++++++++++++++++++++++++")
         
        user_auth = request.env.user
        _logger.info(user_auth)
        employees = list(request.env['hr.employee'].sudo().search([('user_id', '=', user_auth.id)]))
        todos = request.env['hr.employee'].sudo().search([])
        _logger.info("todos++++++++++++++++++++++++++++++++++++++++++++")
        _logger.info(todos)
        
        _logger.info("user_auth.id++++++++++++++++++++++++++++++++++++++++++++")    
        _logger.info(user_auth.id)
        _logger.info(employees)
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_home_portal_values([]))
        print("employees")
        print(employees)
        _logger.info("employees++++++++++++++++++++++++++++++++++++++++++++")
        _logger.info(employees) 
        
        if len(employees) == 1:
            tipos = request.env['hr.leave.type'].sudo().search([])
            # print(tipos)
            tipos2 = []
            for tipo in tipos:
                tipos2.append(tipo.condicion) 
            _logger.info("tipos2++++++++++++++++++++++++++++++++++++++++++++")
            _logger.info(tipos2)
            
            departments = request.env['hr.department'].sudo().search([])    
            contracts = request.env['hr.contract.type'].sudo().search([])
            horarios = request.env['resource.calendar'].sudo().search([])
            vacantes = request.env['hr.job'].sudo().search([])
            employees_l = request.env['hr.employee'].sudo().search([])
            sedes = request.env['account.analytic.account'].sudo().search([])
            # equipos = request.env['product.template'].sudo().search([('detailed_type', '=', 'consu')])
            # epps = request.env['product.template'].sudo().search([('detailed_type', '=', 'consu')])
            equipos =[]
            epps = []
            requerimientos_lista = []
            values = {
                **values,
                'has_contract' : bool(employees[0].current_contract),
                'payroll_list' : self.get_payroll_certificates(),
                'leaves': self.get_my_leaves(),
                'tipos': tipos,
                'tipos2': tipos2,
                'procesos':departments,
                'contratos':contracts,
                'autorizadores':employees_l,
                'horarios':horarios,
                'vacantes':vacantes,
                'sedes':sedes,
                'equipos':equipos,
                'epps':epps,
                "requerimientos_lista":requerimientos_lista,
            }
            _logger.info("values++++++++++++++++++++++++++++++++++++++++++++")
            _logger.info(values)
            current_year = int(datetime.now().year)
            year = [x for x in range(current_year - 6, current_year)]
            year.sort(reverse=True)
            values.update({'years': year})
            
            return request.render("employee_reports_portal.portal_my_home_employee", values)
        
        else:
            _logger.info("sin empleado++++++++++++++++++++++++++++++++++++++++++++")
            _logger.info(values)
            values = self._prepare_portal_layout_values()
            values.update(self._prepare_home_portal_values([]))
            return request.render("portal.portal_my_home", values)

    @route(['/company_logo/<int:company_id>'], type='http', auth="public")
    def company_logo(self, company_id, **kwargs):
        company = request.env['res.company'].sudo().browse(company_id)
        if company and company.company_logo:
            image_data = base64.b64decode(company.company_logo)
            return Response(image_data, mimetype='image/png')
        return Response('No image', status=404)