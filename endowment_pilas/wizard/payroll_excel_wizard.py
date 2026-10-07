import io
import os
import base64
import openpyxl

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.modules import get_module_resource

from openpyxl.styles import Alignment
from datetime import datetime, date

import logging

_logger = logging.getLogger(__name__)



class PayrollExcelWizard(models.TransientModel):
    _name = 'hr.payroll.excel.wizard'
    _description = 'Wizard para Reporte de Nómina a Excel'

    date_from = fields.Date(string="Fecha Desde")
    date_to = fields.Date(string="Fecha Hasta")
    payslip_run_id = fields.Many2one('hr.payslip.run', string="Lote de Nómina")

    plantilla_excel = fields.Binary(string='Plantilla Excel', help='Sube la plantilla de Excel para usar en el reporte. Si está vacío, se usará la plantilla por defecto.')
    plantilla_excel_name = fields.Char(string='Nombre Archivo Plantilla')

    #file_input = fields.Binary(string="Archivo Excel del Cliente", required=True)
    #file_name = fields.Char(string="Nombre del Archivo")

    

    def action_generate_excel_report(self):


        """
        Genera el reporte Excel de recibos de nómina filtrados.
        """
        # 1. DEFINICIÓN DEL DOMINIO Y BÚSQUEDA
        domain = [('state', '=', 'done')]
        if self.date_from: domain.append(('date_from', '>=', self.date_from))
        if self.date_to: domain.append(('date_to', '<=', self.date_to))
        if self.payslip_run_id: domain.append(('payslip_run_id', '=', self.payslip_run_id.id))

        payslips = self.env['hr.payslip'].search(domain)
        if not payslips:
            raise UserError(_("No se encontró ningún recibo de nómina para los filtros"))

        # 2. CARICAMENTO MODELLO (Ottimizzato per non corrompere il file)
        output = io.BytesIO()

        if self.plantilla_excel:
            input_buffer = io.BytesIO(base64.b64decode(self.plantilla_excel))
            wb = openpyxl.load_workbook(
                input_buffer,
                data_only=False,
                keep_links=False  # 🔥 IMPORTANTE
            )
        else:
            file_name_in_data = 'DIVITIASSAS.xlsx'
            path = get_module_resource('endowment_pilas', 'data', file_name_in_data)

            if not path or not os.path.exists(path):
                raise UserError(_("El modelo %s no se encuentra.") % file_name_in_data)

            wb = openpyxl.load_workbook(
                path,
                data_only=False,
                keep_links=False  # 🔥 IMPORTANTE
            )

        # Cerchiamo il foglio "Liquidaciones" o quello attivo
        try:
            sheet = wb['Liquidaciones']
        except KeyError:
            sheet = wb.active

        # 3. LLENADO DE DATOS (Empezamos en la fila 19 porque la 17 y 18 son encabezados)
        row_num = 19
        row_counter = 1

        for payslip in payslips:
            employee = payslip.employee_id
            contract = payslip.contract_id
            correction_status_value = payslip.correction_status if hasattr(payslip, 'correction_status') else 'No'


            ############################## type identification#########################
            # Obtenemos el registro del tipo de identificación

            mapeo_id = {
                'Cédula de ciudadanía': 'CC',
                'Cédula de extranjería': 'CE',
                'Tarjeta de Identidad': 'TI',
                'Registro Civil': 'RC',
                'Pasaporte': 'PA',
                'Permiso por Protección Temporal': 'PT', # El que viste en la lista
                'PEP (Permiso Especial de Permanencia)': 'PE',
                'NIT': 'NI',
                'ID Extranjera': 'CE',
                'Documento de identificación extranjero': 'CD'
            }

            # 1. Obtenemos el registro
            tipo_doc_rec = employee.employee_address_home.l10n_latam_identification_type_id

            # 2. Extraemos el nombre (string)
            nombre_largo = tipo_doc_rec.name or ''

            # 3. Aplicamos el mapeo que definimos antes para que salga "CC", "CE", etc.
            # mapeo_id es el diccionario que definimos en el paso anterior
            tipo_doc_abreviado = mapeo_id.get(nombre_largo, nombre_largo)
            #####################################################################
            tipo_cotizante_excel_label = 'NINGUNA' 
            if contract:
                if contract.pila_tipo_trabajador_id:
                    # Usamos el nombre del nuevo campo configurable, si tiene algo (como '1.Dependiente')
                    tipo_cotizante_excel_label = contract.pila_tipo_trabajador_id.name or "NINGUNA"
                #elif contract.tipo_trabajador:
                    # --- CORRECCIÓN AQUÍ ---
                    # Método recomendado para obtener la etiqueta legible del campo Selection
                    #tipo_cotizante_excel_label = dict(contract._fields['tipo_trabajador'].selection).get(contract.tipo_trabajador, '')

            sub_cotizante_excel_label = 'NINGUNO' 
            if contract:
                if contract.pila_subtipo_trabajador_id:
                    sub_cotizante_excel_label = contract.pila_subtipo_trabajador_id.name or "NINGUNA"
                #elif contract.sub_tipo_trabajador:
                    # --- CORRECCIÓN AQUÍ ---
                    # Método recomendado para obtener la etiqueta legible del campo Selection
                    #sub_cotizante_excel_label = dict(contract._fields['sub_tipo_trabajador'].selection).get(contract.sub_tipo_trabajador, '')

            # --- NUEVO: Lógica para 'Horas Laboradas' ---

            dias_cotizados_pension = 0.0
            dias_cotizados_salud = 0.0
            dias_cotizados_arl = 0.0
            dias_cotizados_ccf = 0.0
            
            horas_laboradas = 0.0
            dias_laborados = 0.0  # 👈 nuevo acumulador

            for worked_day_line in payslip.worked_days_line_ids:
                days = worked_day_line.number_of_days
                hours = worked_day_line.number_of_hours
                code = worked_day_line.code
                
                # DÍAS: Se acumulan todos para que coincida con el total (sum) del XML
                dias_laborados += days 
                
                # HORAS: Únicamente si es el código de asistencia
                if code == 'WORK100': 
                    horas_laboradas += hours

                
                # 2. ACUMULACIÓN DE DÍAS COTIZADOS 
                # Se utiliza el código de la línea del día trabajado directamente 
                # para determinar a qué columna PILA se suma.
                
                if code == 'pension':
                    dias_cotizados_pension += days
                elif code == 'salud':
                    dias_cotizados_salud += days
                elif code == 'arl':
                    dias_cotizados_arl += days
                elif code == 'ccf':
                    dias_cotizados_ccf += days


            ####################################################

            # Inicializa ambas etiquetas
            es_extranjero_label = 'No'
            es_residente_label = 'No'

            # Lógica para 'Extranjero' (Basada en País)
            if employee and employee.country_id:
                if employee.country_id.name != 'Colombia':
                    es_extranjero_label = 'Si'
                    
            if employee and employee.is_non_resident:
                es_residente_label = 'Si'

            
            
            # --- Lógica: Fecha de radicación en el exterior ---
            fecha_radicacion = ''
            if employee and getattr(employee, 'date_resident', False):
                fecha_radicacion = employee.date_resident  # Debe ser tipo Date en tu modelo

             # --- Lógica: Fecha inicio del contrato ---
            fecha_inicio_contrato = ''
            if contract and getattr(contract, 'date_start', False):
                fecha_inicio_contrato = contract.date_start  # Tipo Date normalmente


            # --- Lógica: ING (Ingreso) ---
            valor_ing = 'NO'
            if fecha_inicio_contrato:
                es_periodo_ingreso = False
                # Validación de rango
                if self.date_from and self.date_to:
                    if self.date_from <= fecha_inicio_contrato <= self.date_to:
                        es_periodo_ingreso = True
                elif self.date_from:
                    if fecha_inicio_contrato >= self.date_from:
                        es_periodo_ingreso = True
                elif self.date_to:
                    if fecha_inicio_contrato <= self.date_to:
                        es_periodo_ingreso = True
                else:
                    es_periodo_ingreso = True

                # Si está en el rango, aplicamos el concepto del contrato
                if es_periodo_ingreso:
                    # Buscamos el código del Many2one, si no hay, ponemos 'X'
                    valor_ing = contract.pila_ingreso_concepto_id.name or 'NO'

            # --- Lógica: Fecha final del contrato ---
            fecha_final_contrato = False
            if contract and getattr(contract, 'date_end', False):
                fecha_final_contrato = contract.date_end

            # --- Lógica: RET (Retiro) ---
            valor_ret = 'NO'
            if fecha_final_contrato:
                es_periodo_retiro = False
                # Validación de rango
                if self.date_from and self.date_to:
                    if self.date_from <= fecha_final_contrato <= self.date_to:
                        es_periodo_retiro = True
                elif self.date_from:
                    if fecha_final_contrato >= self.date_from:
                        es_periodo_retiro = True
                elif self.date_to:
                    if fecha_final_contrato <= self.date_to:
                        es_periodo_retiro = True
                else:
                    es_periodo_retiro = True

                # Si está en el rango, aplicamos el concepto del contrato
                if es_periodo_retiro:
                    # Buscamos el código del Many2one, si no hay, ponemos 'X'
                    valor_ret = contract.pila_retiro_concepto_id.name or 'NO'

            # Inicializar un diccionario para guardar los valores por defecto 'NO'
            # Asegúrate de que los códigos aquí coincidan con los de tu campo 'novelty_code'
            # 1. Inicializamos todas las novedades simples en 'NO' por defecto
            novelty_values = {code: 'NO' for code in ['TDE', 'TAE', 'TDP', 'TAP']} # Agrega aquí tus códigos
            
            report_start_date = self.date_from
            report_end_date = self.date_to

            afp_destino = ""
            eps_destino = ""

            # Supongamos que recorremos las administradoras configuradas en el contrato
            # o donde las tengas relacionadas (ajusta 'contract.administradora_ids' según tu modelo)
            if contract.administradoras_ids:
                for admin_line in contract.administradoras_ids:
                    # 1. ¿Es una administradora de tipo Pensión y tiene Traslado marcado?
                    if admin_line.type_entity == 'pension' and admin_line.traslado:
                        if admin_line.list_administradora_destino_id:
                            # Tomamos el nombre de la entidad destino de la lista maestra
                            afp_destino = admin_line.list_administradora_destino_id.name.upper()

                    # 2. ¿Es una administradora de tipo Salud y tiene Traslado marcado?
                    elif admin_line.type_entity == 'salud' and admin_line.traslado:
                        if admin_line.list_administradora_destino_id:
                            # Tomamos el nombre de la entidad destino de la lista maestra
                            eps_destino = admin_line.list_administradora_destino_id.name.upper()

            # Inicializar VSP con valores vacíos/por defecto
            valor_vsp = 'NO'
            fecha_vsp_str = ''

            # ----------------------------------------------------
            # 🆕 Lógica Simplificada para VSP (Variación Salario)
            # ----------------------------------------------------

            # 1. Obtenemos la fecha de cambio del campo dedicado del contrato
            fecha_cambio_sueldo = contract.date_wage_change

            if fecha_cambio_sueldo and report_start_date and report_end_date:
                
                # 2. Verificamos si la fecha de cambio cae DENTRO del rango del reporte.
                # El filtro que usa el reporte: [self.date_from, self.date_to]
                if report_start_date <= fecha_cambio_sueldo <= report_end_date:
                    
                    # Si la fecha de cambio está dentro del periodo, es VSP = 'SI'
                    valor_vsp = 'SI'
                    fecha_vsp_str = fecha_cambio_sueldo # Ya es un objeto date

            #####################################################################
            valor_vst = 'NO'

            payslips_vst = self.env['hr.payslip'].search([
                ('employee_id', '=', contract.employee_id.id),
                ('date_from', '>=', report_start_date),
                ('date_to', '<=', report_end_date),
                ('state', '=', 'done')
            ])

            if payslips_vst:
                transitory_lines = payslips_vst.mapped('line_ids').filtered(
                    lambda l: l.salary_rule_id.is_payment_transitory and l.total > 0
                )

                if transitory_lines:
                    valor_vst = 'SI'

            # ----------------------------------------------------
            # 📌 Lógica para Ausencias (Usando hr.leave - Solicitudes de Ausencia)
            # ----------------------------------------------------

            # Definición de códigos relevantes y Inicialización a 'NO'
            ABSENCE_CODES = ['SLN', 'IGE', 'LMA', 'VAL-LR', 'AVP', 'VCT', 'IRL']

            # Tu búsqueda actual (sin cambios)
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', report_end_date),
                ('date_to', '>=', report_start_date),
            ])

            # Filtramos solo las que nos interesan
            relevant_leaves = []
            if leaves:
                for leave in leaves:
                    novelty_code = leave.holiday_status_id.pila_novelty_code
                    if novelty_code and novelty_code in ABSENCE_CODES:
                        relevant_leaves.append(leave)

            # Si no hay hojas relevantes, añadimos un None para que el bucle haga una iteración con todo "NO"
            if not relevant_leaves:
                relevant_leaves = [None]


            for current_leave in relevant_leaves:
                absence_novelties = {code: {'value': 'NO', 'start': '', 'end': ''} for code in ABSENCE_CODES}
                count_lma = 0
                count_ige = 0

                if current_leave:
                    novelty_code = current_leave.holiday_status_id.pila_novelty_code
                    if novelty_code == 'LMA':
                        count_lma = int(current_leave.number_of_days)
                    elif novelty_code == 'IGE':
                        count_ige = int(current_leave.number_of_days)
                        
                    absence_novelties[novelty_code]['value'] = current_leave.holiday_status_id.name or 'SI'

                    if novelty_code != 'AVP':
                        absence_novelties[novelty_code]['start'] = current_leave.date_from.date()
                        absence_novelties[novelty_code]['end'] = current_leave.date_to.date()

                # Usaremos el nombre (label) para el Excel.
                # El método _get_selection_label() toma el nombre legible del campo de selección.
                correction_status_excel_value = payslip.correction_status if hasattr(payslip, 'correction_status') else 'no'

                salario_mensual = contract.wage if contract else 0.0

                        # ----------------------------------------------------
                # 📌 LÓGICA PARA SALARIO INTEGRAL Y VARIABLE
                # ----------------------------------------------------

                # 1. Salario Integral (True/False del contrato -> SI/NO)
                if contract and contract.wage_integral:
                    integral_excel_value = 'SI'
                else:
                    integral_excel_value = 'NO'

                # 2. Salario Variable (True/False del contrato -> SI/NO)
                if contract and contract.wage_variable:
                    variable_excel_value = 'SI'
                else:
                    variable_excel_value = 'NO'

                ##################################################################

                # ADMINISTRADORAS
                pension_admin = contract.get_admin_by_type('pension')
                salud_admin = contract.get_admin_by_type('salud')
                arl_admin = contract.get_admin_by_type('arl')
                ccf_admin = contract.get_admin_by_type('ccf')


                # --------------------------- Lógica de Alto Riesgo ---------------------------
                alto_riesgo_selection = self.env['hr.contract'].fields_get(allfields=['alto_riesgo']
                )['alto_riesgo']['selection']

                alto_riesgo_label = ''
                if contract and contract.alto_riesgo:
                    alto_riesgo_label = dict(alto_riesgo_selection).get(contract.alto_riesgo, '')


                claves_reporte = [
                    'valor_cotizacion_pension', 'valor_cotizacion_salud', 'valor_cotizacion_riesgo',
                    'valor_cotizacion_ccf', 'cotizacion_voluntaria_afiliado', 'cotizacion_voluntaria_empleador',
                    'fondo_solidaridad', 'fondo_subsistencia', 'valor_no_retenido', 'total_aportes',
                    'valor_upc', 'valor_incapacidad_eg', 'valor_licencia_maternidad',
                    'ibc','ibc_otros_parafiscales',
                    'valor_cotizacion_sena', 'valor_cotizacion_icbf', 'valor_cotizacion_esap',
                    'valor_cotizacion_men', 'exonerado_1607'
                ]

                # 2. Inicializar con 0.0 (es mejor para cálculos numéricos)
                valores_reglas = {k: 0.0 for k in claves_reporte}

                # 3. Recorrer las líneas de la nómina
                for line in payslip.line_ids:
                    # Obtenemos la marca de la regla
                    tipo = line.salary_rule_id.tipo_reporte_excel

                    # Si la regla tiene una marca y esa marca está en nuestras claves
                    if tipo and tipo in valores_reglas:
                        valores_reglas[tipo] += line.total

                ######################Otras tarifas ##################################
                admins = payslip.contract_id.administradoras_ids
                #t_ccf = sum(admins.mapped('tarifa_ccf')) or 0.0
                t_sena = sum(admins.mapped('tarifa_sena')) or 0.0
                t_icbf = sum(admins.mapped('tarifa_icbf')) or 0.0
                t_esap = sum(admins.mapped('tarifa_esap')) or 0.0
                t_men = sum(admins.mapped('tarifa_men')) or 0.0

                ################Clase ################################

                valor_clase = contract.clase if contract.clase else ''

                ################### centro trabajo ################################

                #nombre_departamento = contract.department_id.name if contract.department_id else ''
                val_centro_trabajo = ""
                if contract.work_center_id:
                    val_centro_trabajo = contract.work_center_id.name.upper()
                else:
                    # SI NO HAY REGISTRO, PASAMOS EL VALOR FIJO
                    val_centro_trabajo = "RIESGO III"

                #####################Actividad Economica #######################################
                actividad_economica = contract.economic_activitity if contract.economic_activitity else ''

                ################################upc adicional################################
                mapeo_id = {
                    'Cédula de ciudadanía': 'CC',
                    'Tarjeta de identidad': 'TI',
                    'Registro civil': 'RC',
                    'Cédula de extranjería': 'CE',
                    'Pasaporte': 'PA',
                    'NIT': 'NI',
                    'Permiso Especial de Permanencia': 'PE',
                    'Permiso por Protección Temporal': 'PT',
                }

                tipo_doc_upc_rec = employee.l10n_latam_identification_type_id

                # 2. Extraemos el nombre (o cadena vacía si no hay)
                nombre_doc_upc = tipo_doc_upc_rec.name or ''

                # 3. Buscamos la abreviatura en el mapeo. Si no está, dejamos el nombre original.
                tipo_doc_upc_abreviado = mapeo_id.get(nombre_doc_upc, nombre_doc_upc)

                # 4. Obtenemos el número y le quitamos puntos/guiones/espacios
                raw_upc = employee.upc_identification_number or ''
                numero_upc_limpio = str(raw_upc).replace('.', '').replace('-', '').strip()
                # 4. Obtenemos el número de identificación adicional
                #numero_upc = employee.upc_identification_number or ''

                data = [
                    row_counter,                                      # 1 (A)
                    tipo_doc_abreviado or 'CC',                                # 2 (B) - Debe ser 'CC', 'CE', etc.
                    str(employee.employee_address_home.vat or '').replace('.', '').replace('-', '').strip(), # 3 (C)
                    (employee.employee_address_home.last_name or '').upper(), # 4 (D)
                    (employee.employee_address_home.second_last_name or '').upper(), # 5 (E)
                    (employee.employee_address_home.first_name or '').upper(), # 6 (F)
                    (employee.employee_address_home.middle_name or '').upper(), # 7 (G)
                    (employee.employee_address_home.state_id.name or 'BOGOTA').upper(), # 8 (H)
                    (employee.employee_address_home.city_id.name or 'BOGOTA').upper(), # 9 (I)
                    tipo_cotizante_excel_label or '1.DEPENDIENTE',   # 10 (J)
                    sub_cotizante_excel_label or 'NINGUNO',           # 11 (K)
                    horas_laboradas or 0,                             # 12 (L)
                    es_extranjero_label or 'NO',                      # 13 (M)
                    es_residente_label or 'NO',                       # 14 (N)
                    fecha_radicacion or '',                           # 15 (O)

                    # --- BLOQUE DE MARCAS (SI/NO) ---
                    valor_ing or 'NO',                                # 16 (P) ING
                    fecha_inicio_contrato or '',                      # 17 (Q) Fecha ING
                    valor_ret or 'NO',                                # 18 (R) RET
                    fecha_final_contrato or '',                       # 19 (S) Fecha RET
                    novelty_values.get('TDE', 'NO'),                  # 20 (T)
                    novelty_values.get('TAE', 'NO'),                  # 21 (U)
                    novelty_values.get('TDP', 'NO'),                  # 22 (V)
                    novelty_values.get('TAP', 'NO'),                  # 23 (W)
                    valor_vsp or 'NO',                                # 24 (X) VSP
                    fecha_vsp_str or '',                              # 25 (Y) Fecha VSP
                    'NO',                                             # 26 (Z) VST (Variación Transitoria)

                    # --- BLOQUE AUSENCIAS (3 columnas por cada una) ---
                    absence_novelties['SLN']['value'], absence_novelties['SLN']['start'], absence_novelties['SLN']['end'], # 27,28,29
                    absence_novelties['IGE']['value'], absence_novelties['IGE']['start'], absence_novelties['IGE']['end'], # 30,31,32
                    absence_novelties['LMA']['value'], absence_novelties['LMA']['start'], absence_novelties['LMA']['end'], # 33,34,35
                    absence_novelties['VAL-LR']['value'], absence_novelties['VAL-LR']['start'], absence_novelties['VAL-LR']['end'], # 36,37,38
                    absence_novelties['AVP']['value'],                # 39 (Solo marca)
                    absence_novelties['VCT']['value'], absence_novelties['VCT']['start'], absence_novelties['VCT']['end'], # 40,41,42
                    absence_novelties['IRL']['value'], absence_novelties['IRL']['start'], absence_novelties['IRL']['end'], # 43,44,45

                    correction_status_excel_value,  # 46 Corrección / IRP numérico
                    salario_mensual or 0,                             # 47
                    integral_excel_value or 'NO',                     # 48
                    variable_excel_value or 'NO',                     # 49

                    # --- PENSION ---
                    pension_admin.get_pension_label() if pension_admin else 'NINGUNO', # 50
                    dias_laborados or 0,                      # 51
                    valores_reglas['ibc'] or 0,               # 52
                    contract.get_tarifa_by_type('pension') or 0,      # 53
                    valores_reglas['valor_cotizacion_pension'] or 0,  # 54
                    alto_riesgo_label or 'NO',                        # 55
                    valores_reglas['cotizacion_voluntaria_afiliado'] or 0, # 56
                    valores_reglas['cotizacion_voluntaria_empleador'] or 0,# 57
                    valores_reglas['fondo_solidaridad'] or 0,         # 58
                    valores_reglas['fondo_subsistencia'] or 0,        # 59
                    valores_reglas['valor_no_retenido'] or 0,         # 60
                    valores_reglas['total_aportes'] or 0,             # 61
                    pension_admin.get_pension_destino_label() if pension_admin else 'NINGUNO', # 62

                    # --- SALUD ---
                    salud_admin.get_salud_label() if salud_admin else 'NINGUNO', # 63
                    dias_laborados or 0,                        # 64
                    valores_reglas['ibc'] or 0,                 # 65
                    contract.get_tarifa_by_type('salud') or 0,        # 66
                    valores_reglas['valor_cotizacion_salud'] or 0,    # 67
                    valores_reglas['valor_upc'] or 0,                 # 68
                    count_ige or '',                                  # 69 N° Autorización EG
                    valores_reglas['valor_incapacidad_eg'] or 0,      # 70
                    count_lma or '',                                  # 71 N° Autorización LMA
                    valores_reglas['valor_licencia_maternidad'] or 0, # 72
                    salud_admin.get_salud_destino_label() if salud_admin else 'NINGUNO', # 73

                    # --- RIESGOS (ARL) ---
                    arl_admin.get_arl_label() if arl_admin else 'NINGUNA', # 74
                    dias_laborados or 0,                          # 75
                    valores_reglas['ibc'] or 0,                # 76
                    contract.get_tarifa_by_type('arl') or 0,          # 77
                    valor_clase or '1',                               # 78
                    #nombre_departamento or '',                        # 79
                    val_centro_trabajo or '',                        # 79
                    actividad_economica or '',                        # 80
                    valores_reglas['valor_cotizacion_riesgo'] or 0,   # 81

                    # --- CAJA Y PARAFISCALES ---
                    dias_laborados or 0,                          # 82
                    ccf_admin.get_ccf_label() if ccf_admin else 'NINGUNA', # 83
                    valores_reglas['ibc'] or 0,                   # 84
                    contract.get_tarifa_by_type('ccf') or 0,          # 85
                    valores_reglas['valor_cotizacion_ccf'] or 0,      # 86
                    valores_reglas['ibc_otros_parafiscales'] or 0,    # 87
                    t_sena or 0,                                      # 88
                    valores_reglas['valor_cotizacion_sena'] or 0,     # 89
                    t_icbf or 0,                                      # 90
                    valores_reglas['valor_cotizacion_icbf'] or 0,     # 91
                    t_esap or 0,                                      # 92
                    valores_reglas['valor_cotizacion_esap'] or 0,     # 93
                    t_men or 0,                                       # 94
                    valores_reglas['valor_cotizacion_men'] or 0,      # 95
                    valores_reglas['exonerado_1607'] or 0,         # 96
                    tipo_doc_upc_abreviado if numero_upc_limpio else '', # 97: Solo pon tipo si hay número
                    numero_upc_limpio,
                ]



                def clean_text(val):
                    if not val:
                        return ""
                    # Elimina saltos de línea y retornos de carro que rompen el XML de Excel
                    v = str(val).replace('\n', '').replace('\r', '').strip().upper()
                    return "" if v in ['NONE', 'FALSE'] else v


                def clean_id(val):
                    v = str(val or '').replace('.', '').replace('-', '').strip()
                    return "" if v.upper() in ['', 'NONE', 'FALSE', 'NINGUNO'] else v

                def limit(val, max_len):
                    return val[:max_len] if val else ""

                # --- PROCESO DE ESCRITURA CON VALIDACIÓN DE FORMATO ---
                for col_num, cell_value in enumerate(data, start=1):
                    cell = sheet.cell(row=row_num, column=col_num)

                     # ================= DEBUG FILA QUE FALLA EN APORTES =================
                    if row_counter == 9:
                        val_debug = str(cell_value or '')
                        _logger.error(
                            "DEBUG PILA FILA 9 | row_excel=%s | col=%s | len=%s | valor=%s",
                            row_num,
                            col_num,
                            len(val_debug),
                            val_debug
                        )

                        if len(val_debug) > 30:
                            _logger.error(
                                "ERROR LONGITUD PILA FILA 9 | row_excel=%s | col=%s | len=%s | valor=%s",
                                row_num,
                                col_num,
                                len(val_debug),
                                val_debug
                            )

                        if col_num in [8, 9, 27, 30, 33, 50, 62, 63, 73, 74, 79, 80, 83]:
                            _logger.error(
                                "CAMPO CRITICO PILA FILA 9 | col=%s | valor=%s",
                                col_num,
                                val_debug
                            )
                    # ================================================================

                    # ---------------- COLUMNA 1 ----------------
                    # ---------------- COLUMNA 1 (A) ----------------
                    if col_num == 1:
                        cell.value = row_counter
                        cell.number_format = '0'
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                        
                        continue

                    # ---------------- IDs ----------------
                    if col_num in [2, 3, 97, 98]:
                        cell.value = clean_id(cell_value)
                        cell.data_type = 's'
                        continue

                    # ---------------- NOMBRES ----------------
                    if col_num in [4, 5, 6, 7]:
                        #cell.value = clean_text(cell_value)
                        val = clean_text(cell_value)
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                        cell.value = limit(val, 20)  # ajusta según PILA real
                        continue

                    # ---------------- ADMINISTRADORAS ----------------
                    if col_num in [50, 62, 63, 73, 74, 83]:
                        val = clean_text(cell_value)
                        val = val if val else "NINGUNA"
                        cell.value = val   # ✔ SIN LIMIT
                        continue   

                    # ---------------- CORRECCIÓN / IRP ----------------
                    if col_num == 46:
                        val = clean_text(cell_value)

                        if val not in ['NO', 'ACTUAL', 'CORRECCIÓN']:
                            val = 'NO'

                        cell.value = val
                        cell.data_type = 's'
                        continue

                    # ---------------- SI / NO ----------------
                    if col_num in [48, 49, 96]:
                        val = str(cell_value or '').strip().upper()
                        cell.value = "SI" if val in ['SI', 'TRUE', '1', 'S'] else "NO"
                        continue

                    # ---------------- CLASE RIESGO ----------------
                    if col_num == 55:
                        val = str(cell_value or '').strip()
                        cell.value = "Sin Riesgo" if val in ['', '5', 'NONE', 'FALSE', '0'] else val
                        continue

                    # ---------------- CENTRO TRABAJO ----------------
                    if col_num == 79:
                        val = clean_text(cell_value)
                        val = val if val else "RIESGO III"
                        cell.value = val
                        cell.data_type = 's'
                        continue

                    # ---------------- ACTIVIDAD ECONOMICA ----------------
                    if col_num == 80:
                        val = clean_text(cell_value)
                        cell.value = val
                        cell.data_type = 's'
                        continue

                    # ---------------- DINERO ----------------
                    if col_num in [47, 52, 54, 56, 57, 58, 59, 60, 61, 65, 68, 70, 72, 76, 81, 84, 86, 87, 89, 91, 93, 95]:
                        try:
                            num = float(cell_value or 0)
                            if num != 0:
                                cell.value = int(num)
                                cell.number_format = '#,##0'
                            else:
                                cell.value = "" # <--- Cambiado para que quede en blanco si es 0
                            cell.alignment = Alignment(horizontal='right', vertical='center')
                        except:
                            cell.value = ""
                        continue


                    # ---------------- PORCENTAJES ----------------
                    if col_num in [53, 66, 77, 85, 88, 90, 92, 94]:
                        try:
                            val = float(str(cell_value or 0).replace('%', '').strip())
                            cell.value = val / 100 if val > 1 else val
                            cell.number_format = '0.00%'
                        except:
                            cell.value = ""
                        continue

                    # ---------------- NOVEDADES LISTAS DESPLEGABLES ----------------
                    if col_num in [27, 30, 33, 36, 39, 40, 43]:
                        val = clean_text(cell_value)
                        cell.value = val if val else "NO"
                        cell.data_type = 's'
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                        continue

                    # ---------------- FECHAS ----------------
                    if col_num in [15, 17, 19, 25, 28, 29, 31, 32, 34, 35, 37, 38, 41, 42, 44, 45]:
                        if cell_value:
                            try:
                                # Si ya es date/datetime, lo usamos. Si es string, lo convertimos.
                                if isinstance(cell_value, (date, datetime)):
                                    val_fecha = cell_value
                                else:
                                    val_fecha = fields.Date.from_string(cell_value)
                                
                                cell.value = val_fecha
                                cell.number_format = 'yyyy-mm-dd' # Estándar requerido por PILA
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                            except:
                                cell.value = ""
                        else:
                            cell.value = ""
                        continue

                    # ---------------- NUMÉRICOS GENERALES ----------------
                    if (47 <= col_num <= 78) or (81 <= col_num <= 95) or col_num == 12:
                        try:
                            num = float(cell_value or 0)
                            if num != 0:
                                cell.value = int(num)
                                cell.number_format = '#,##0'
                            else:
                                cell.value = ""
                        except:
                            cell.value = ""
                        continue

                    # ---------------- DEFAULT ----------------

                    # Este código solo se ejecutará si NO entró en ninguno de los IF anteriores
                    val = clean_text(cell_value)
                    cell.value = limit(val, 30)
                    cell.alignment = Alignment(horizontal='left', vertical='center')

                # --- ESTAS DOS LÍNEAS DEBEN IR AQUÍ (Fuera del bucle de columnas) ---
                row_num += 1
            row_counter += 1

        # fuera de todos los bucles
        last_data_row = row_num - 1

        if sheet.max_row > last_data_row:
            sheet.delete_rows(last_data_row + 1, sheet.max_row - last_data_row)

        # 1. Guardar directamente con openpyxl (SIN pandas, SIN xlsxwriter)
        output = io.BytesIO()
        wb.save(output)

        # 2. Obtener datos
        out_data = output.getvalue()
        output.close()

        # 3. Crear el adjunto
        attachment = self.env['ir.attachment'].create({
            'name': f"PILA_DIVITIASSAS_{fields.Date.today()}.xlsx",
            'type': 'binary',
            'datas': base64.b64encode(out_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # 4. Descargar
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


    def _format_pila(self, value, length, field_type='text'):
        """ Limpieza de datos y ajuste de ancho fijo para PILA """
        # 1. Manejo de Nulos y limpieza básica
        if value is None or (isinstance(value, float) and pd.isna(value)) or value is False:
            val = ""
        else:
            val = str(value).strip().upper()

        # 2. Lógica para Novedades (Campos de marca X)
        # Si la longitud es 1 o 2 y es una marca de "SI/NO"
        if field_type == 'text' and length <= 2:
            if val in ['SI', 'S', 'X', '1', 'TRUE']:
                return 'X'.ljust(length)[:length]
            return ' '.ljust(length)[:length]

        # 3. Lógica para Números Enteros (IBC, Cotizaciones, Cédulas)
        if field_type == 'num':
            # Eliminamos decimales si vienen (ej: "1500.0" -> "1500")
            clean_num = val.split('.')[0]
            # Dejamos solo los dígitos
            clean_num = "".join(filter(str.isdigit, clean_num))
            # Rellenamos con ceros a la izquierda
            return clean_num.zfill(length)[:length]

        # 4. Lógica para Tarifas (7 decimales)
        if field_type == 'float_7dec':
            try:
                num = float(val)
                # Formato 0.1600000
                return f"{num:.7f}".ljust(length)[:length]
            except:
                return "0.0000000".ljust(length)[:length]

        # 5. Texto Normal (Nombres, Apellidos, Códigos)
        # Alinea a la izquierda y rellena con espacios
        return val.ljust(length)[:length]


    def action_generate_txt_pila(self):
        """ Genera el Archivo Plano (TXT) con la lógica completa del Excel """
        self.ensure_one()

        # 1. MISMA BÚSQUEDA Y FILTROS QUE EL EXCEL
        domain = [('state', '=', 'done')]
        if self.date_from: domain.append(('date_from', '>=', self.date_from))
        if self.date_to: domain.append(('date_to', '<=', self.date_to))
        if self.payslip_run_id: domain.append(('payslip_run_id', '=', self.payslip_run_id.id))

        payslips = self.env['hr.payslip'].search(domain)
        if not payslips:
            raise UserError(_("No se encontraron nóminas validadas para los filtros seleccionados."))

        company = self.env.company
        lines = []

        # 2. REGISTRO TIPO 1 (Encabezado de Empresa - 305 caracteres)
        periodo_salud = self.date_from.strftime('%Y-%m') if self.date_from else "2026-02"
        periodo_nosalud = self.date_from.strftime('%Y-%m') if self.date_from else "2026-01"
        
        t1 = "011" # Tipo registro y modalidad
        t1 += "0001" # Secuencia
        t1 += self._format_pila(company.name, 200) # Nombre empresa
        t1 += "S" # Tipo identificación (S para NI)
        t1 += self._format_pila(company.vat or '0', 16, 'num') # NIT
        t1 += "0" # Dígito verificación
        t1 += "E" # Tipo aportante
        t1 = t1.ljust(235)
        t1 += "S" # Acción
        t1 += "54" # Código operador
        t1 += self._format_pila("COLMENA", 40) # ARL
        t1 += periodo_nosalud.replace('-', '') # Periodo Pensión
        t1 += periodo_salud.replace('-', '') # Periodo Salud
        t1 = t1.ljust(305)
        lines.append(t1)

        # 3. REGISTRO TIPO 2 (Detalle Empleados - 693 caracteres)
        row_counter = 1
        for payslip in payslips:
            employee = payslip.employee_id
            contract = payslip.contract_id
            address = employee.employee_address_home

            # --- Lógica de Reglas Salariales ---
            claves = ['ibc', 'valor_cotizacion_pension', 'valor_cotizacion_salud', 
                      'valor_cotizacion_riesgo', 'valor_cotizacion_ccf']
            valores = {k: 0.0 for k in claves}
            for line in payslip.line_ids:
                tipo = line.salary_rule_id.tipo_reporte_excel
                if tipo in valores:
                    valores[tipo] += line.total

            # --- Lógica de Días y Horas ---
            dias_p = 0
            horas_lab = 0
            for wd in payslip.worked_days_line_ids:
                if wd.code == 'pension': dias_p += int(wd.number_of_days)
                if wd.code == 'WORK100': horas_lab += int(wd.number_of_hours)

            # --- Lógica de Novedades (ING, RET, VSP) ---
            flag_ing = "X" if contract.date_start and self.date_from <= contract.date_start <= self.date_to else " "
            flag_ret = "X" if contract.date_end and self.date_from <= contract.date_end <= self.date_to else " "
            flag_vsp = "X" if contract.date_wage_change and self.date_from <= contract.date_wage_change <= self.date_to else " "

            # --- Construcción de la línea ---
            l2 = "02"
            l2 += self._format_pila(row_counter, 5, 'num')
            
            # Identificación
            tipo_doc = {'Cédula de ciudadanía': 'CC', 'NIT': 'NI'}.get(address.l10n_latam_identification_type_id.name, 'CC')
            l2 += self._format_pila(tipo_doc, 2)
            l2 += self._format_pila(address.vat, 16)
            
            # Tipo Cotizante
            tipo_coti = "".join(filter(str.isdigit, contract.pila_tipo_trabajador_id.name or '01'))[:2].zfill(2)
            sub_coti = "".join(filter(str.isdigit, contract.pila_subtipo_trabajador_id.name or '00'))[:2].zfill(2)
            l2 += tipo_coti + sub_coti + " " # Extranjero
            l2 += "63001" # Depto/Ciudad (Ajustar según necesidad)

            # Nombres (Mayúsculas)
            l2 += self._format_pila(address.last_name, 20)
            l2 += self._format_pila(address.second_last_name, 30)
            l2 += self._format_pila(address.first_name, 20)
            l2 += self._format_pila(address.middle_name, 30)

            # Marcas de Novedad (Posiciones 136-150 aprox)
            l2 += flag_ing + flag_ret + " " + " " + " " + " " + flag_vsp + " "
            # Ausencias (SLN, IGE, LMA...)
            l2 += " " * 7 # Espacios para ausencias si no hay lógica hr.leave activa

            # Administradoras
            l2 += self._format_pila(contract.get_admin_by_type('pension').code or '230301', 6)
            l2 += " " * 6 # Pension destino
            l2 += self._format_pila(contract.get_admin_by_type('salud').code or 'EPS001', 6)
            l2 += " " * 6 # Salud destino
            l2 += self._format_pila(contract.get_admin_by_type('ccf').code or 'CCF01', 6)

            # Días y Salario
            l2 += self._format_pila(dias_p, 2, 'num') * 4 # Repite días para P, S, R, C
            l2 += self._format_pila(int(contract.wage), 9, 'num')
            l2 += "X" if contract.wage_integral else " "
            
            # IBC y Aportes
            ibc_val = self._format_pila(int(valores['ibc']), 9, 'num')
            l2 += ibc_val * 4 # IBC para P, S, R, C
            
            # Tarifas y Cotizaciones (Ejemplo Pensión)
            l2 += self._format_pila(contract.get_tarifa_by_type('pension') or 0.16, 9, 'float_7dec')
            l2 += self._format_pila(int(valores['valor_cotizacion_pension']), 9, 'num')
            l2 += "0" * 27 # Aportes solidaridad/subsistencia/no retenidos

            # Salud
            l2 += self._format_pila(contract.get_tarifa_by_type('salud') or 0.125, 9, 'float_7dec')
            l2 += self._format_pila(int(valores['valor_cotizacion_salud']), 9, 'num')
            l2 += "0" * 9 # UPC

            # Finalización de línea (Ancho fijo)
            l2 = l2.ljust(660)
            l2 += self._format_pila(horas_lab, 3, 'num') # Horas laboradas al final
            
            lines.append(l2.ljust(693))
            row_counter += 1

        # 4. EXPORTACIÓN
        final_txt = "\r\n".join(lines) + "\r\n"
        attachment = self.env['ir.attachment'].create({
            'name': f"PILA_PLANO_{fields.Date.today()}.txt",
            'type': 'binary',
            'datas': base64.b64encode(final_txt.encode('latin-1', 'ignore')),
            'mimetype': 'text/plain',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }