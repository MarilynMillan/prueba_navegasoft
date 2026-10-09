import base64
import io
import logging
import re
import unicodedata
import zipfile
from datetime import date, datetime

import openpyxl
from dateutil.relativedelta import relativedelta
from openpyxl.styles import Alignment

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PILA_TEMPLATE_ATTACHMENT_PARAM = 'endowment_pilas.pila_template_attachment_id'


class PayrollExcelWizard(models.TransientModel):
    _name = 'hr.payroll.excel.wizard'
    _description = 'Wizard para Reporte de Nómina a Excel'

    date_from = fields.Date(string="Fecha Desde")
    date_to = fields.Date(string="Fecha Hasta")
    payslip_run_id = fields.Many2one('hr.payslip.run', string="Lote de Nómina")

    plantilla_excel = fields.Binary(
        help=(
            'Sube la plantilla de Excel para usar en el reporte. Si está '
            'vacío, se usará la plantilla guardada para la compañía.'
        ),
    )
    plantilla_excel_name = fields.Char(string='Nombre Archivo Plantilla')
    plantilla_guardada_nombre = fields.Char(
        string='Plantilla actual',
        compute='_compute_plantilla_guardada',
    )
    plantilla_guardada_fecha = fields.Datetime(
        string='Última actualización',
        compute='_compute_plantilla_guardada',
    )

    tipo_planilla = fields.Selection(
        [
            ('E', 'E - Planilla Empleados Empresas'),
            ('A', 'A - Planilla Empleados Adicionales'),
            ('I', 'I - Planilla Independientes'),
            ('Y', 'Y - Planilla Independientes Empresas'),
            ('S', 'S - Planilla Empleados de Independientes'),
            ('N', 'N - Planilla Correcciones'),
            ('M', 'M - Planilla Mora'),
            ('H', 'H - Plantilla Madres Comunitarias'),
            ('T', 'T - Planilla Sistema General de Participación'),
            ('F', 'F - Planilla Faltante SGP'),
            ('J', 'J - Planilla Aportes en Sentencia Judicial'),
            ('K', 'K - Planilla Estudiantes'),
            ('O', 'O - Obligaciones Determinadas Por La UGPP'),
            ('B', 'B - Piso Protección Total'),
        ],
        default='E',
        required=True,
    )

    tipo_aportante = fields.Selection(
        [
            ('EMPLEADOR', 'EMPLEADOR'),
            ('INDEPENDIENTE', 'INDEPENDIENTE'),
        ],
        default='EMPLEADOR',
        required=True,
    )

    sucursal_codigo = fields.Char(string="Código", required=True)

    sucursal_nombre = fields.Char(
        string="Nombre",
        default='PRINCIPAL',
        required=True,
    )

    administradora_riesgos = fields.Selection(
        [
            ('COLMENA', 'COLMENA'),
            ('COLPATRIA ARP', 'COLPATRIA ARP'),
            ('COLSANITAS ARL', 'COLSANITAS ARL'),
            ('FONDO DE RIESGOS LABORALES', 'FONDO DE RIESGOS LABORALES'),
            ('LA EQUIDAD SEGUROS', 'LA EQUIDAD SEGUROS'),
            ('POSITIVA COMPAÑIA DE SEGUROS', 'POSITIVA COMPAÑIA DE SEGUROS'),
            ('SEGUROS BOLIVAR', 'SEGUROS BOLIVAR'),
            ('SEGUROS DE VIDA AURORA', 'SEGUROS DE VIDA AURORA'),
        ],
        default='COLMENA',
        required=True,
    )

    planilla_asociada_fecha = fields.Date(string="Fecha")

    planilla_asociada_clave = fields.Char(
        string="Clave"
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        attachment = self._get_company_template_attachment()
        if attachment:
            if 'plantilla_excel' in fields_list:
                values['plantilla_excel'] = attachment.datas
            if 'plantilla_excel_name' in fields_list:
                values['plantilla_excel_name'] = attachment.name
        return values

    # =========================
    # HELPERS PILA
    # =========================

    def _pila_norm(self, value):
        if not value:
            return ''
        # Convertir a string, quitar espacios extremos y pasar a mayúsculas
        value = str(value).strip().upper()
        value = value.replace('\n', ' ').replace('\r', ' ')

        # Eliminar comillas dobles y simples que dañan el match.
        value = value.replace('"', '').replace("'", "")

        # Quitar acentos y tildes
        value = unicodedata.normalize('NFD', value)
        value = ''.join(
            c for c in value
            if unicodedata.category(c) != 'Mn'
        )

        # Colapsar espacios múltiples en uno solo
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    def _get_defined_name_values(self, wb, name):
        values = []

        try:
            defined_name = wb.defined_names[name]
        except Exception:
            return values

        for sheet_name, coord in defined_name.destinations:
            ws = wb[sheet_name]

            for row in ws[coord]:
                for cell in row:
                    if cell.value:
                        values.append(str(cell.value).strip())

        return values

    def _match_catalog_value(self, raw_value, allowed_values):
        raw_norm = self._pila_norm(raw_value)

        for value in allowed_values:
            if self._pila_norm(value) == raw_norm:
                return value

        return False

    def _normalize_location_pila(
        self,
        wb,
        departamento_odoo,
        ciudad_odoo
    ):

        departamentos = self._get_defined_name_values(
            wb,
            'RGDIVIDEPTO'
        )

        if not departamentos:
            raise UserError(self.env._("No se encontró RGDIVIDEPTO"))

        dept_map = {
            'BOGOTA': 'BOGOTA_D.E.',
            'BOGOTA DC': 'BOGOTA_D.E.',
            'BOGOTA D C': 'BOGOTA_D.E.',
            'BOGOTA D.C.': 'BOGOTA_D.E.',
            'BOGOTA D.E.': 'BOGOTA_D.E.',
            'NARINO': 'NARIÑO',
        }

        city_map = {
            'BOGOTA': 'BOGOTA',
            'BOGOTA DC': 'BOGOTA',
            'BOGOTA D C': 'BOGOTA',
            'BOGOTA D.C.': 'BOGOTA',
            'BOGOTA D.E.': 'BOGOTA',
            'CARTAGENA DE INDIAS': 'CARTAGENA',
        }

        dept_raw = self._pila_norm(departamento_odoo)
        city_raw = self._pila_norm(ciudad_odoo)

        dept_candidate = dept_map.get(dept_raw, dept_raw)
        city_candidate = city_map.get(city_raw, city_raw)

        departamento_pila = self._match_catalog_value(
            dept_candidate,
            departamentos
        )

        if not departamento_pila:
            raise UserError(self.env._(
                "Departamento inválido PILA:\n%s",
                departamento_odoo,
            ))

        ciudades = self._get_defined_name_values(
            wb,
            departamento_pila
        )

        ciudad_pila = self._match_catalog_value(
            city_candidate,
            ciudades
        )

        if not ciudad_pila:
            raise UserError(self.env._(
                "Ciudad inválida PILA:\n%s",
                ciudad_odoo,
            ))

        return departamento_pila, ciudad_pila

    def _validate_pila_value(
        self,
        errores,
        employee,
        campo,
        value,
        allowed_values,
        required=False
    ):
        value = str(value or '').strip()

        if not value or value.upper() in ['NINGUNA', 'NINGUNO', 'NO', 'FALSE']:
            if required:
                errores.add(
                    "%s | %s vacío."
                    % (employee.display_name, campo)
                )
            return ''

        # Normalizamos el valor que viene de Odoo (ej: elimina comillas o espacios)
        value_norm = self._pila_norm(value)

        # Normalizar también cada opción del catálogo de Excel antes de comparar.
        for allowed in allowed_values:
            if self._pila_norm(allowed) == value_norm:
                return allowed

        errores.add(
            "%s | %s inválido para PILA: %s"
            % (employee.display_name, campo, value)
        )

        return ''

    def _get_named_range_values(self, wb, range_name):
        try:
            defined_name = wb.defined_names[range_name]
        except Exception:
            return []

        values = []

        for sheet_name, coord in defined_name.destinations:
            ws = wb[sheet_name]

            for row in ws[coord]:
                for cell in row:
                    if cell.value:
                        values.append(str(cell.value).strip())

        return values

    def _get_company_template_param(self):
        return '%s.%s' % (
            PILA_TEMPLATE_ATTACHMENT_PARAM,
            self.env.company.id,
        )

    def _get_company_template_attachment(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            self._get_company_template_param()
        )

        try:
            attachment_id = int(param or 0)
        except ValueError:
            return self.env['ir.attachment']

        attachment = self.env['ir.attachment'].sudo().browse(attachment_id)
        if (
            not attachment.exists()
            or not attachment.datas
            or attachment.company_id != self.env.company
        ):
            return self.env['ir.attachment']

        return attachment

    @api.depends_context('company')
    def _compute_plantilla_guardada(self):
        attachment = self._get_company_template_attachment()
        for wizard in self:
            wizard.plantilla_guardada_nombre = attachment.name or False
            wizard.plantilla_guardada_fecha = attachment.write_date or False

    def _save_company_template_attachment(self):
        attachment_model = self.env['ir.attachment'].sudo()
        attachment = self._get_company_template_attachment()
        file_name = self.plantilla_excel_name or 'pila_template.xlsx'

        values = {
            'name': file_name,
            'type': 'binary',
            'datas': self.plantilla_excel,
            'company_id': self.env.company.id,
            'mimetype': (
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        }

        if attachment:
            attachment.write(values)
        else:
            attachment = attachment_model.create(values)
            self.env['ir.config_parameter'].sudo().set_param(
                self._get_company_template_param(),
                attachment.id
            )

        return attachment

    @api.onchange('plantilla_excel', 'plantilla_excel_name')
    def _onchange_plantilla_excel(self):
        for wizard in self:
            if wizard.plantilla_excel:
                attachment = wizard._save_company_template_attachment()
                wizard.plantilla_guardada_nombre = attachment.name
                wizard.plantilla_guardada_fecha = attachment.write_date

    def _get_template_content(self):
        if self.plantilla_excel:
            self._save_company_template_attachment()
            template_data = self.plantilla_excel
        else:
            attachment = self._get_company_template_attachment()
            if not attachment:
                raise UserError(self.env._(
                    "Debe cargar una plantilla PILA para la compañía %s. La "
                    "plantilla cargada se guardará para futuros reportes de "
                    "esta compañía.",
                    self.env.company.display_name,
                ))
            template_data = attachment.datas

        try:
            return base64.b64decode(template_data)
        except Exception as error:
            raise UserError(self.env._(
                "La plantilla PILA no es un archivo válido."
            )) from error

    def _validate_generate_excel_fields(self):
        missing_fields = []
        if not self.tipo_planilla:
            missing_fields.append(self.env._("Tipo de planilla"))
        if not self.tipo_aportante:
            missing_fields.append(self.env._("Tipo de aportante"))
        if not self.sucursal_codigo:
            missing_fields.append(self.env._("Código de sucursal"))
        if not self.sucursal_nombre:
            missing_fields.append(self.env._("Nombre de sucursal"))
        if not self.administradora_riesgos:
            missing_fields.append(self.env._("Administradora de riesgos"))

        if missing_fields:
            raise UserError(self.env._(
                "Complete estos campos antes de generar el Excel:\n%s",
                "\n".join("- %s" % field for field in missing_fields),
            ))

    def action_generate_excel_report(self):
        """Genera el reporte Excel de recibos de nómina filtrados."""
        self._validate_generate_excel_fields()
        template_content = self._get_template_content()

        # 1. DEFINICIÓN DEL DOMINIO Y BÚSQUEDA
        domain = [('state', 'in', ['done', 'paid'])]
        if self.date_from:
            domain.append(('date_from', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_to', '<=', self.date_to))
        if self.payslip_run_id:
            domain.append(('payslip_run_id', '=', self.payslip_run_id.id))

        payslips = self.env['hr.payslip'].search(domain)
        if not payslips:
            raise UserError(self.env._(
                "No se encontró ningún recibo de nómina para los filtros"
            ))

        # 2. CARICAMENTO MODELLO (Ottimizzato per non corrompere il file)
        input_buffer = io.BytesIO(template_content)
        wb = openpyxl.load_workbook(
            input_buffer,
            data_only=False,
            keep_vba=False,
            keep_links=False
        )

        if 'DatosPruebaEmp' not in wb.sheetnames:
            raise UserError(self.env._(
                "No existe DatosPruebaEmp. Hojas: %s",
                wb.sheetnames,
            ))

        if 'Liquidaciones' not in wb.sheetnames:
            raise UserError(self.env._(
                "No existe Liquidaciones. Hojas: %s",
                wb.sheetnames,
            ))

        datos_sheet = wb['DatosPruebaEmp']
        sheet = wb['Liquidaciones']



        datos_sheet.sheet_state = 'veryHidden'
        sheet.sheet_state = 'visible'

        wb.active = wb.sheetnames.index('Liquidaciones')

        # =====================================================
        # ENCABEZADO PILA
        # =====================================================

        fecha_base = self.date_to or fields.Date.today()

        # Salud = periodo actual
        periodo_salud = fecha_base.strftime('%Y-%m')

        # Pensión = periodo anterior
        periodo_pension = (
            fecha_base - relativedelta(months=1)
        ).strftime('%Y-%m')

        # ---------------- PERIODO ----------------
        sheet['A10'] = periodo_pension
        sheet['C10'] = periodo_salud

        # ---------------- TIPO PLANILLA ----------------
        sheet['D10'] = self.tipo_planilla or 'E'

        # ---------------- PLANILLA ASOCIADA ----------------
        sheet['E10'] = (
            self.planilla_asociada_fecha.strftime('%Y-%m-%d')
            if self.planilla_asociada_fecha
            else ''
        )

        sheet['F10'] = self.planilla_asociada_clave or ''

        # ---------------- SUCURSAL ----------------
        sheet['G10'] = self.sucursal_codigo or ''
        sheet['H10'] = self.sucursal_nombre or 'PRINCIPAL'

        # ---------------- TIPO APORTANTE ----------------
        sheet['I10'] = self.tipo_aportante or 'EMPLEADOR'

        # ---------------- ADMINISTRADORA RIESGOS ----------------
        sheet['K10'] = self.administradora_riesgos or 'COLMENA'

        # 3. LLENADO DE DATOS (Empezamos en la fila 19 porque la 17 y 18 son encabezados)
        row_num = 19
        row_counter = 1

        errores_pila = set()

        # Agrupar las nóminas por empleado
        payslips_by_employee = {}
        for payslip in payslips:
            emp = payslip.employee_id
            if emp not in payslips_by_employee:
                payslips_by_employee[emp] = []
            payslips_by_employee[emp].append(payslip)

        for employee, emp_payslips in payslips_by_employee.items():
            # Tomar el contrato y datos base de la nómina más reciente
            emp_payslips_sorted = sorted(emp_payslips, key=lambda p: p.date_to, reverse=True)
            payslip = emp_payslips_sorted[0]
            contract = payslip.contract_id

            # Obtener el rango de fechas consolidado del empleado
            emp_date_from = min(p.date_from for p in emp_payslips)
            emp_date_to = max(p.date_to for p in emp_payslips)

            correction_status_value = 'No'
            for p in emp_payslips:
                if hasattr(p, 'correction_status') and p.correction_status not in [False, 'no', 'No']:
                    correction_status_value = p.correction_status
                    break


            ############################## type identification#########################
            # Obtenemos el registro del tipo de identificación

            mapeo_id = {
                'Cédula de ciudadanía': 'CC',
                'Cédula de extranjería': 'CE',
                'Tarjeta de Identidad': 'TI',
                'Registro Civil': 'RC',
                'Pasaporte': 'PA',
                'Permiso por Protección Temporal': 'PT',
                'PEP (Permiso Especial de Permanencia)': 'PE',
                'ID Extranjera': 'CE',
                'Documento de identificación extranjero': 'CD',
                'NIT': 'CC',

            }

            # 1. Obtenemos el registro
            tipo_doc_rec = employee.employee_address_home.l10n_latam_identification_type_id

            # 2. Extraemos el nombre (string)
            nombre_largo = tipo_doc_rec.name or ''

            # 3. Aplicamos el mapeo que definimos antes para que salga "CC", "CE", etc.
            # mapeo_id es el diccionario que definimos en el paso anterior
            tipo_doc_abreviado = mapeo_id.get(nombre_largo, nombre_largo)
            tipo_doc_abreviado = self._pila_norm(tipo_doc_abreviado)

            _logger.error(
                "DOC RAW=%r | DOC NORMAL=%r",
                nombre_largo,
                tipo_doc_abreviado
            )
            TIPOS_DOC_VALIDOS = [
                'CC',
                'CE',
                'TI',
                'RC',
                'PA',
                'CD',
                'SC',
                'PE',
                'PT',
            ]

            if tipo_doc_abreviado not in TIPOS_DOC_VALIDOS:
                errores_pila.add(
                    "%s | Tipo documento inválido PILA: %s"
                    % (
                        employee.display_name,
                        tipo_doc_abreviado
                    )
                )
            #####################################################################
            tipo_cotizante_excel_label = '1. Dependiente'
            if contract:
                if contract.pila_tipo_trabajador_id:
                    # Usamos el nombre del nuevo campo configurable, si tiene algo (como '1.Dependiente')
                    tipo_cotizante_excel_label = contract.pila_tipo_trabajador_id.name or "1. Dependiente"

            sub_cotizante_excel_label = 'NINGUNO'
            if contract:
                if contract.pila_subtipo_trabajador_id:
                    sub_cotizante_excel_label = contract.pila_subtipo_trabajador_id.name or "NINGUNA"
            #####################################################################################

            horas_laboradas = 0.0
            dias_laborados = 0.0  # 👈 nuevo acumulador

            dias_cotizados_pension = 0.0
            dias_cotizados_salud = 0.0
            dias_cotizados_arl = 0.0
            dias_cotizados_ccf = 0.0

            # Consolidar días y horas de todas las nóminas del empleado
            for p_slip in emp_payslips:
                for worked_day_line in p_slip.worked_days_line_ids:
                    days = worked_day_line.number_of_days
                    hours = worked_day_line.number_of_hours
                    code = worked_day_line.code

                    # DÍAS: Se acumulan todos los días procesados de la nómina
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


            # =========================================================================
            # 🟢 AJUSTE DE PRECISIÓN Y VALIDACIÓN TOTAL (FUERA DEL BUCLE FOR)
            # =========================================================================

            # 1. Convertimos a número entero completo para destruir decimales flotantes (Ej: 30.00014 -> 30)
            dias_laborados = int(round(dias_laborados, 0))

            # 2. VALIDACIÓN DEFINITIVA: Al estar fuera del bucle, evalúa la suma real final.
            # Si la nómina está mal hecha y suma 31, 37, 45, etc., saltará la alerta para que la arreglen.
            """if dias_laborados > 30:
                errores_pila.add(
                    "%s | Días laborados inválidos: %s. Máximo permitido 30."
                    % (employee.display_name, dias_laborados)
                )"""

            if dias_laborados < 0:
                errores_pila.add(
                    "%s | Días laborados inválidos: %s."
                    % (employee.display_name, dias_laborados)
                )

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

                    valor_ret = contract.pila_retiro_concepto_id.name or 'NO'

            # 1. Inicializamos todas las novedades simples en 'NO' por defecto
            novelty_values = {code: 'NO' for code in ['TDE', 'TAE', 'TDP', 'TAP']} # Agrega aquí tus códigos

            if contract and contract.pila_novelty_ids:

                lineas_novedad = contract.pila_novelty_ids


                for nov_line in lineas_novedad:

                    # Código PILA configurado (TDE, TAE, TDP, TAP)
                    code_novelty = (
                        nov_line.novelty_type_id.code
                        if nov_line.novelty_type_id
                        else False
                    )

                    fecha_ini = nov_line.date_start
                    fecha_fin = nov_line.date_end

                    # Validar que el código exista en el diccionario
                    if code_novelty and code_novelty in novelty_values:

                        # Validación de intersección de fechas
                        if (
                            fecha_ini
                            and self.date_from
                            and self.date_to
                            and fecha_ini <= self.date_to
                            and (
                                not fecha_fin
                                or fecha_fin >= self.date_from
                            )
                        ):

                            novelty_values[code_novelty] = 'SI'

            ############################################################################################
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

            for p_slip in emp_payslips:
                transitory_lines = p_slip.mapped('line_ids').filtered(
                    lambda l: getattr(l.salary_rule_id, 'is_payment_transitory', False) and l.total > 0
                )
                if transitory_lines:
                    valor_vst = 'SI'
                    break

            # ----------------------------------------------------
            # 📌 Lógica para Ausencias (Usando hr.leave - Solicitudes de Ausencia)
            # ----------------------------------------------------

            # Definición de códigos relevantes y Inicialización a 'NO'
            ABSENCE_CODES = ['SLN', 'IGE', 'LMA', 'VAL-LR', 'AVP', 'VCT', 'IRL']

            # Buscar ausencias en el rango consolidado del empleado
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', emp_date_to),
                ('date_to', '>=', emp_date_from),
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
                correction_status_raw = correction_status_value or 'no'

                mapeo_correccion = {
                    'no': 'NO',
                    'actual': 'ACTUAL',
                    'coreccion': 'CORRECCIÓN',
                }

                # Fallback para asegurarse de que las opciones con mayúsculas estén contempladas
                if isinstance(correction_status_raw, str):
                    correction_status_raw = correction_status_raw.lower()

                correction_status_excel_value = mapeo_correccion.get(correction_status_raw, 'NO')

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
                    'ibc','ibc_pension', 'ibc_arl','ibc_caja_c','ibc_otros_parafiscales','valor_cotizacion_sena', 'valor_cotizacion_icbf', 'valor_cotizacion_esap',
                    'valor_cotizacion_men', 'exonerado_1607'
                ]

                # 2. Inicializar con 0.0 (es mejor para cálculos numéricos)
                valores_reglas = {k: 0.0 for k in claves_reporte}

                # 3. Consolidar las líneas de todas las nóminas del empleado
                for p_slip in emp_payslips:
                    for line in p_slip.line_ids:
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
                    'Cédula de extranjería': 'CE',
                    'Tarjeta de Identidad': 'TI',
                    'Registro Civil': 'RC',
                    'Pasaporte': 'PA',
                    'Permiso por Protección Temporal': 'PT',
                    'PEP (Permiso Especial de Permanencia)': 'PE',
                    'ID Extranjera': 'CE',
                    'Documento de identificación extranjero': 'CD',
                    'NIT': 'CC',


                }

                tipo_doc_upc_rec = employee.l10n_latam_identification_type_id

                # 2. Extraemos el nombre (o cadena vacía si no hay)
                nombre_doc_upc = tipo_doc_upc_rec.name or ''

                # 3. Buscamos la abreviatura en el mapeo
                tipo_doc_upc_abreviado = mapeo_id.get(
                    nombre_doc_upc,
                    nombre_doc_upc
                )

                tipo_doc_upc_abreviado = self._pila_norm(
                    tipo_doc_upc_abreviado
                )

                # 4. Número UPC
                raw_upc = employee.upc_identification_number or ''

                numero_upc_limpio = str(raw_upc).replace(
                    '.',
                    ''
                ).replace(
                    '-',
                    ''
                ).strip()

                # 5. Validación PILA
                if (
                    numero_upc_limpio
                    and tipo_doc_upc_abreviado
                    and tipo_doc_upc_abreviado not in TIPOS_DOC_VALIDOS
                ):
                    errores_pila.add(
                        "%s | Tipo documento UPC inválido PILA: %s"
                        % (
                            employee.display_name,
                            tipo_doc_upc_abreviado
                        )
                    )
                # 4. Obtenemos el número de identificación adicional
                #numero_upc = employee.upc_identification_number or ''

                ##################################################################

                if not employee.employee_address_home.state_id:
                    errores_pila.add(
                        "%s | No tiene departamento/state configurado en el contacto."
                        % employee.display_name
                    )

                if not employee.employee_address_home.city_id:
                    errores_pila.add(
                        "%s | No tiene ciudad configurada en el contacto."
                        % employee.display_name
                    )

                departamento_pila = ''
                ciudad_pila = ''

                if employee.employee_address_home.state_id and employee.employee_address_home.city_id:
                    departamento_pila, ciudad_pila = self._normalize_location_pila(
                        wb,
                        employee.employee_address_home.state_id.name,
                        employee.employee_address_home.city_id.name
                    )

                #########################################################################

                lista_conceptos_pila = self._get_defined_name_values(wb, 'RGINCO')

                # 🟢 CORRECCIÓN: Si el Excel no expone el rango global (vuelve []),
                # cargamos las opciones oficiales del operador para que la validación no quede vacía.
                if not lista_conceptos_pila:
                    lista_conceptos_pila = [
                        'NO',
                        'X',
                        'Todos los sistemas (ARL, AFP, CCF, EPS)',
                        'Solo Salud, Pensión y CCF',
                        'Solo Salud'
                    ]

                # Limpiamos los textos que vienen del registro relacional de Odoo
                valor_ing = (valor_ing or 'NO').strip()
                valor_ret = (valor_ret or 'NO').strip()

                # Validamos contra la estructura interna normalizada
                valor_ing = self._validate_pila_value(
                    errores_pila, employee, 'ING', valor_ing, lista_conceptos_pila
                ) or 'NO'

                valor_ret = self._validate_pila_value(
                    errores_pila, employee, 'RET', valor_ret, lista_conceptos_pila
                ) or 'NO'

                # =========================================================
                # VALIDACIONES PILA ANTES DE ARMAR DATA
                # =========================================================
                novedad_map = {
                'INCAPACIDAD 100 %': 'INCAPACIDAD GENERAL',
                'INCAPACIDAD 100%': 'INCAPACIDAD GENERAL',
                'INCAPACIDAD 66.66 %': 'INCAPACIDAD GENERAL',
                'INCAPACIDAD 66.66%': 'INCAPACIDAD GENERAL',
                'SUSPENSION': 'LICENCIA NO REMUNERADA', # 🟢 Mapea "Suspensión" a la opción aceptada por PILA
                'LICENCIA DE LUTO': 'LICENCIA REMUNERADA',
            }


                # 1) Novedades / licencias
                novedades_permitidas = {
                    'SLN': ['NO', 'LICENCIA NO REMUNERADA', 'COMISIÓN DE SERVICIO'],
                    'IGE': ['NO', 'INCAPACIDAD GENERAL', 'LICENCIA POR CUIDADO DE LA NIÑEZ'],
                    'LMA': ['NO', 'LICENCIA DE MATERNIDAD (LMA)', 'LICENCIA PARENTAL FLEXIBLE (MEDIO TIEMPO)'],
                    'VAL-LR': ['NO', 'VACACIONES', 'LICENCIA REMUNERADA'],
                    'AVP': ['NO', 'SI'],
                    'VCT': ['NO', 'SI'],
                }

                for code, permitidos in novedades_permitidas.items():

                    valor_novedad = absence_novelties[code]['value']

                    # =====================================================
                    # NORMALIZAR NOMBRES ODOO -> PILA
                    # =====================================================

                    valor_novedad_norm = self._pila_norm(valor_novedad)

                    valor_novedad = novedad_map.get(
                        valor_novedad_norm,
                        valor_novedad
                    )

                    # Guardamos el valor ya normalizado
                    absence_novelties[code]['value'] = valor_novedad

                    self._validate_pila_value(
                        errores_pila,
                        employee,
                        f"Novedad {code}",
                        valor_novedad,
                        permitidos
                    )

                # 2) IRL debe ser numérico
                valor_irl = absence_novelties['IRL']['value']

                if self._pila_norm(valor_irl) in ['', 'NO', 'NONE', 'FALSE']:
                    valor_irl_excel = 0
                else:
                    try:
                        valor_irl_excel = int(float(valor_irl))
                    except Exception:
                        errores_pila.add(
                            "%s | IRL inválido: %s. Debe ser numérico."
                            % (employee.display_name, valor_irl)
                        )
                        valor_irl_excel = 0

                # =========================================================
                # VALIDACIÓN ADMINISTRADORAS PILA
                # =========================================================

                # Listas reales desde la plantilla
                lista_eps = self._get_defined_name_values(wb, 'RGEPS')
                lista_afp = self._get_defined_name_values(wb, 'RGAFP')
                lista_arl = self._get_defined_name_values(wb, 'RGARL')
                lista_ccf = self._get_defined_name_values(wb, 'RGCCF')

                # 🟢 FALLBACK DE EMERGENCIA: Si el Excel no expone los rangos globales (vuelven []),
                # cargamos respaldos con las opciones principales para que el validador no quede vacío.
                if not lista_arl:
                    lista_arl = ['COLMENA', 'COLPATRIA ARP', 'COLSANITAS ARL', 'POSITIVA COMPAÑIA DE SEGUROS', 'SEGUROS BOLIVAR', 'LA EQUIDAD SEGUROS']
                if not lista_eps:
                    lista_eps = ['SURALICUOTA', 'SANITAS', 'COMPENSAR', 'NUEVA EPS', 'SALUD TOTAL', 'COOMEVA']
                if not lista_afp:
                    lista_afp = ['PROTECCION', 'PORVENIR', 'COLFONDOS', 'SKANDIA', 'COLPENSIONES']
                if not lista_ccf:
                    lista_ccf = ['COMPENSAR', 'COLSUBSIDIO', 'CAFAM', 'COMFENALCO']

                # ORIGEN: Evaluación segura con operador ternario y remoción estricta de espacios (.strip())
                pension_label = (pension_admin.get_pension_label() if pension_admin else '').strip()
                salud_label = (salud_admin.get_salud_label() if salud_admin else '').strip()
                #arl_label = (arl_admin.get_arl_label() if arl_admin else '').strip()   # ✔ ¡Saneado!
                ccf_label = (ccf_admin.get_ccf_label() if ccf_admin else '').strip()

                arl_label = ''
                if contract and contract.department_id:
                    # 1. Buscamos el Centro de Costos de la compañía que contenga el departamento del contrato
                    centro_costo = self.env['hr.centrocostos'].search([
                        ('company_id', '=', payslip.company_id.id),
                        ('departamentos', 'in', contract.department_id.id)
                    ], limit=1)

                    if centro_costo:
                        # 2. Buscamos en las administradoras configuradas en la Compañía
                        # Filtramos las líneas buscando el Centro de Costos y tu nuevo campo exclusivo
                        arl_admin_company = payslip.company_id.administradoras_ids.filtered(
                            lambda a: a.ccostos == centro_costo.name and a.list_administradora_arl_id
                        )

                        if arl_admin_company:
                            # 3. Extraemos el nombre de la ARL del campo list_administradora_arl_id
                            arl_label = arl_admin_company[0].list_administradora_arl_id.name

                # Fallback de Seguridad: Si el departamento no está enlazado a un Centro de Costos,
                # extraemos la primera ARL válida configurada en la compañía para que el archivo no salga vacío.
                if not arl_label:
                    arl_admin_default = payslip.company_id.administradoras_ids.filtered(lambda a: a.list_administradora_arl_id)
                    if arl_admin_default:
                        arl_label = arl_admin_default[0].list_administradora_arl_id.name

                # Limpieza estricta de la cadena para el Excel
                arl_label = (arl_label or '').strip()

                # DESTINO
                pension_destino = (pension_admin.get_pension_destino_label() if pension_admin else '').strip()
                salud_destino = (salud_admin.get_salud_destino_label() if salud_admin else '').strip()

                # --- PROCESO DE VALIDACIÓN CONTRA EL ARCHIVO DE PRUEBA ---

                # AFP origen
                pension_label = self._validate_pila_value(
                    errores_pila, employee, "AFP origen", pension_label, lista_afp
                ) or ''

                # EPS origen
                salud_label = self._validate_pila_value(
                    errores_pila, employee, "EPS origen", salud_label, lista_eps
                ) or ''


                # ARL (Ya no fallará si el contrato anterior venía vacío o incompleto)
                arl_label = self._validate_pila_value(
                    errores_pila, employee, "ARL", arl_label, lista_arl
                ) or ''

                # CCF
                ccf_label = self._validate_pila_value(
                    errores_pila, employee, "CCF", ccf_label, lista_ccf
                ) or ''

                # AFP destino
                if pension_admin and pension_admin.traslado:
                    pension_destino = self._validate_pila_value(
                        errores_pila, employee, "AFP destino", pension_destino, lista_afp
                    ) or ''

                # EPS destino
                if salud_admin and salud_admin.traslado:
                    salud_destino = self._validate_pila_value(
                        errores_pila, employee, "EPS destino", salud_destino, lista_eps
                    ) or ''



                data = [
                    row_counter,                                      # 1 (A)
                    tipo_doc_abreviado or 'CC',                                # 2 (B) - Debe ser 'CC', 'CE', etc.
                    str(employee.employee_address_home.vat or '').replace('.', '').replace('-', '').strip(), # 3 (C)
                    (employee.employee_address_home.last_name or '').upper(), # 4 (D)
                    (employee.employee_address_home.second_last_name or '').upper(), # 5 (E)
                    (employee.employee_address_home.first_name or '').upper(), # 6 (F)
                    (employee.employee_address_home.middle_name or '').upper(), # 7 (G)
                    departamento_pila, # 8 (H)
                    ciudad_pila, # 9 (I)
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
                    #absence_novelties['IRL']['value'], absence_novelties['IRL']['start'], absence_novelties['IRL']['end'], # 43,44,45
                    valor_irl_excel, #43
                    absence_novelties['IRL']['start'],  # 44
                    absence_novelties['IRL']['end'],    # 45


                    correction_status_excel_value,  # 46 Corrección / IRP numérico
                    salario_mensual or 0,                             # 47
                    integral_excel_value or 'NO',                     # 48
                    variable_excel_value or 'NO',                     # 49

                    # --- PENSION ---
                    #pension_admin.get_pension_label() if pension_admin else 'NINGUNA', # 50
                    pension_label, # 50
                    dias_laborados or 0,                      # 51
                    valores_reglas['ibc_pension'] or 0,               # 52
                    contract.get_tarifa_by_type('pension') or 0,      # 53
                    valores_reglas['valor_cotizacion_pension'] or 0,  # 54
                    alto_riesgo_label or 'NO',                        # 55
                    valores_reglas['cotizacion_voluntaria_afiliado'] or 0, # 56
                    valores_reglas['cotizacion_voluntaria_empleador'] or 0,# 57
                    valores_reglas['fondo_solidaridad'] or 0,         # 58
                    valores_reglas['fondo_subsistencia'] or 0,        # 59
                    valores_reglas['valor_no_retenido'] or 0,         # 60
                    valores_reglas['total_aportes'] or 0,             # 61
                    #pension_admin.get_pension_destino_label() if pension_admin else 'NINGUNA', # 62
                    pension_destino, # 62
                    # --- SALUD ---
                    #salud_admin.get_salud_label() if salud_admin else 'NINGUNA', # 63
                    salud_label,# 63
                    dias_laborados or 0,                        # 64
                    valores_reglas['ibc'] or 0,                 # 65
                    contract.get_tarifa_by_type('salud') or 0,        # 66
                    valores_reglas['valor_cotizacion_salud'] or 0,    # 67
                    valores_reglas['valor_upc'] or 0,                 # 68
                    count_ige or '',                                  # 69 N° Autorización EG
                    valores_reglas['valor_incapacidad_eg'] or 0,      # 70
                    count_lma or '',                                  # 71 N° Autorización LMA
                    valores_reglas['valor_licencia_maternidad'] or 0, # 72
                    #salud_admin.get_salud_destino_label() if salud_admin else 'NINGUNA', # 73
                    salud_destino, # 73


                    # --- RIESGOS (ARL) ---
                    #arl_admin.get_arl_label() if arl_admin else 'NINGUNA', # 74
                    arl_label, # 74
                    dias_laborados or 0,                             # 75
                    valores_reglas['ibc_arl'] or 0,                      # 76
                    contract.tarifa_arl ,                              # 77 (Se divide entre 100 porque openpyxl lo formatea con '%')         # 77
                    valor_clase or '1',                               # 78
                    #nombre_departamento or '',                        # 79
                    val_centro_trabajo or '',                        # 79
                    actividad_economica or '',                        # 80
                    valores_reglas['valor_cotizacion_riesgo'] or 0,   # 81

                    # --- CAJA Y PARAFISCALES ---
                    dias_laborados or 0,                          # 82
                    #ccf_admin.get_ccf_label() if ccf_admin else 'NINGUNA', # 83
                    ccf_label, # 83
                    valores_reglas['ibc_caja_c'] or 0,                       # 84
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

                    # ---------------- 🟢 CONCEPTOS DE INGRESO Y RETIRO (ING / RET) ----------------
                    if col_num in [16, 18]:
                        # 🟢 SOLUCIÓN PUREZA: No llamamos a clean_text() para evitar el .upper().
                        # Limpiamos los saltos de línea a mano, respetando las minúsculas de Odoo.
                        val = str(cell_value or '').replace('\n', '').replace('\r', '').strip()
                        val = val if val and val.upper() not in ['NONE', 'FALSE', '0'] else "NO"

                        # Escribimos el valor idéntico al de la Base de Datos
                        cell.value = val
                        cell.data_type = 's'
                        cell.alignment = Alignment(horizontal='left', vertical='center')
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
                    if col_num in [53, 66, 85, 88, 90, 92, 94]:
                        try:
                            val = float(str(cell_value or 0).replace('%', '').strip())
                            cell.value = val / 100 if val > 1 else val
                            cell.number_format = '0.00%'
                        except:
                            cell.value = ""
                        continue

                    if col_num == 77:

                        try:
                            val = float(str(cell_value or 0).replace('%', '').replace(',', '.').strip())

                            # 👇 Guardar valor exacto convertido a porcentaje Excel
                            cell.value = val / 100

                            # 👇 Mostrar 3 decimales
                            cell.number_format = '0.000%'

                        except:
                            cell.value = ""

                        continue

                    # ---------------- NOVEDADES LISTAS DESPLEGABLES ----------------
                    if col_num == 43:
                        try:
                            cell.value = int(float(cell_value or 0))
                        except Exception:
                            cell.value = 0
                        cell.number_format = '0'
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                        continue

                    if col_num in [27, 30, 33, 36, 39, 40]:
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
        start_clean_row = row_num
        end_clean_row = sheet.max_row
        max_col = 98

        if end_clean_row >= start_clean_row:
            from openpyxl.styles import Border, Side, PatternFill

            no_border = Border(left=Side(border_style=None),
                               right=Side(border_style=None),
                               top=Side(border_style=None),
                               bottom=Side(border_style=None))
            no_fill = PatternFill(fill_type=None)

            # 1. Limpieza visual y de estilos en el lienzo de Excel
            for row in range(start_clean_row, end_clean_row + 1):
                for col in range(1, max_col + 1):
                    cell = sheet.cell(row=row, column=col)
                    cell.value = None
                    cell.style = 'Normal'
                    cell.border = no_border
                    cell.fill = no_fill
                    cell.comment = None
                    cell.hyperlink = None

            # 2. 🟢 EL TRUCO ABSOLUTO: Eliminar las celdas de la memoria interna de la hoja
            # Esto arranca de raíz las comas fantasmas del CSV que detecta Aportes en Línea
            for row in range(start_clean_row, end_clean_row + 1):
                for col in range(1, max_col + 1):
                    cell_key = (row, col)
                    # Si openpyxl guardó la celda en su diccionario interno, la exterminamos
                    if cell_key in sheet._cells:
                        del sheet._cells[cell_key]

            # 3. Recortar y purgar las listas desplegables (Data Validations)
            if hasattr(sheet, 'data_validations') and sheet.data_validations.dataValidation:
                validaciones_a_mantener = []

                for dv in sheet.data_validations.dataValidation:
                    nuevas_celdas = []

                    for sqref in dv.sqref.ranges:
                        # Cortamos el rango para que muera estrictamente en el último empleado real
                        if sqref.max_row >= start_clean_row:
                            sqref.max_row = start_clean_row - 1

                        # Si el rango modificado sigue siendo válido arriba, se conserva
                        if sqref.max_row >= sqref.min_row:
                            nuevas_celdas.append(sqref)

                    if nuevas_celdas:
                        from openpyxl.worksheet.cell_range import MultiCellRange
                        dv.sqref = MultiCellRange(nuevas_celdas)
                        validaciones_a_mantener.append(dv)

                sheet.data_validations.dataValidation = validaciones_a_mantener

        # 4. Forzado seguro de dimensiones borrando la caché interna
        if hasattr(sheet, '_invalidated_dimensions'):
            sheet._invalidated_dimensions = True

        sheet.calculate_dimension()

        #if sheet.max_row > last_data_row:
            #sheet.delete_rows(last_data_row + 1, sheet.max_row - last_data_row)

        if errores_pila:

            errores_ordenados = sorted(list(errores_pila))

            raise UserError(
                self.env._(
                    "Corrija estos datos antes de generar PILA:\n\n%s",
                    "\n".join(errores_ordenados[:80]),
                )
            )

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        fixed_output = io.BytesIO()

        with zipfile.ZipFile(output, 'r') as zin:
            with zipfile.ZipFile(fixed_output, 'w', zipfile.ZIP_DEFLATED) as zout:

                for item in zin.infolist():

                    content = zin.read(item.filename)

                    if item.filename == 'xl/workbook.xml':

                        xml = content.decode('utf-8')

                        xml = re.sub(
                            r'(<sheet[^>]*name="DatosPruebaEmp"[^>]*sheetId=")\d+(")',
                            r'\g<1>2\2',
                            xml
                        )

                        xml = re.sub(
                            r'(<sheet[^>]*name="Liquidaciones"[^>]*sheetId=")\d+(")',
                            r'\g<1>1\2',
                            xml
                        )

                        content = xml.encode('utf-8')

                    zout.writestr(item, content)

        out_data = fixed_output.getvalue()

        output.close()
        fixed_output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f"PILA_{fields.Date.today()}.xlsx",
            'type': 'binary',
            'datas': base64.b64encode(out_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
