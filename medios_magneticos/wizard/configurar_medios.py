import requests
import json
from datetime import date
from odoo import models, fields, api, _

from odoo.tools import SQL

import logging
_logger = logging.getLogger(__name__)


class WizardConfiguracionExogena(models.TransientModel):
    _name = 'wizard.configuracion.exogena'
    _description = 'Configuración de Información Exógena'
    
    year = fields.Integer(
        'Año', required=True, 
        default=lambda self: date.today().year - 1
    )
    
    response_message = fields.Text('Mensaje de Respuesta', readonly=True)

    def _get_resumen_cuentas_contables(self):
        # Se obtiene el año del wizard
        report = self.env.ref('medios_magneticos.report_account_resumen')  # Reemplaza con tu report_id
        # Configura las opciones. Puedes incluir el filtro por año en el rango de fechas:
        year = self.year
        options = report.get_options({}) #report.get_options(None)
        options = {
            'date': {
                'mode': 'range',
                'date_from': '{}-01-01'.format(year),
                'date_to': '{}-12-31'.format(year),
                'filter': 'custom',
            },
            # Agrega otros filtros u opciones que requiera el reporte
        }
        # Llama a tu handler personalizado
        #for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
        options.setdefault('column_groups', [])
        handler = self.env['l10n_co.custom.account.report.handler']
        domain = handler._get_domain(report, options)
        results = handler._get_query_results(report, options, domain)
        # Aquí puedes procesar o mostrar los resultados como necesites
        _logger.info("Consulta SQL ejecutada. Se obtuvieron %d registros.", len(results))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.resumen.cuentas.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_results': json.dumps(results),
            },
        }
    

    def probar_local(self):
        results = self._get_resumen_cuentas_contables()
        _logger.info("Consulta SQL ejecutada. Se obtuvieron %d registros.", len(results))
        return results
        
        
        # self.ensure_one()
        # base_url = "https://richard.navegasoft.com/exogena"  # Reemplaza con la URL real

        # try:
        #     _logger.info("Iniciando ejecución de probar_local para el año %s", self.year)

        #     # Paso 1: Ejecutar SQL localmente
        #     results = self._get_resumen_cuentas_contables()
        #     _logger.info("Consulta SQL ejecutada. Se obtuvieron %d registros.", len(results))

        #     for row in results:
        #         codigo_cuenta = row[0]
        #         nombre_cuenta = row[1]
        #         total_debito = row[2] or 0.0
        #         total_credito = row[3] or 0.0
        #         valor = total_debito - total_credito

        #         _logger.debug("Procesando cuenta %s: débito=%.2f, crédito=%.2f, valor=%.2f",
        #                     codigo_cuenta, total_debito, total_credito, valor)

        #         payload = {
        #             'codigo_cuenta': codigo_cuenta,
        #             'funcion': 'consultar_cuenta'
        #         }

        #         try:
        #             _logger.debug("Enviando solicitud al API para cuenta %s con payload %s", codigo_cuenta, payload)
        #             response = requests.get(base_url, params=payload, timeout=10)
        #             response.raise_for_status()
        #             data = response.json()
        #             _logger.debug("Respuesta del API para cuenta %s: %s", codigo_cuenta, data)

        #             tipo_suma = data.get('tipo_suma', 'No definido')
        #             concepto = data.get('concepto', nombre_cuenta)
        #             formato = data.get('formato', '1001')

        #         except Exception as e:
        #             tipo_suma = 'Error'
        #             concepto = nombre_cuenta
        #             formato = '1001'
        #             _logger.error("Error al consultar cuenta %s: %s", codigo_cuenta, str(e))

        #         self.env['account.exogena'].create({
        #             'year': self.year,
        #             'cuenta': codigo_cuenta,
        #             'concepto': concepto,
        #             'formato': formato,
        #             'valor': valor,
        #             'tipo_suma': tipo_suma,
        #             'categoria': 'Automática (con API por fila)',
        #         })
        #         _logger.info("Registro creado para cuenta %s", codigo_cuenta)

        #     self.response_message = _("Se ejecutó correctamente y se consultaron las cuentas una a una.")
        #     _logger.info("Proceso completado correctamente para el año %s", self.year)

        # except Exception as e:
        #     self.response_message = _("Error durante la ejecución: %s") % str(e)
        #     _logger.exception("Error crítico en probar_local: %s", str(e))

        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Información Exógena',
        #     'res_model': 'account.exogena',
        #     'view_mode': 'list',
        #     'domain': [('year', '=', self.year)],
        #     'target': 'current',
        # }


    
    def obtener_datos_exogena(self):
        """ Llama a un servidor externo, obtiene datos y los guarda """
        base_url  = "https://richard.navegasoft.com/exogena"  # Reemplaza con la URL real
        
        
        try:
            # Primera petición: buscar_cuentas
            payload_1 = {'year': self.year, 'funcion': 'buscar_cuentas'}
            resp1 = requests.get(base_url, params=payload_1, timeout=30)
            resp1.raise_for_status()
            data1 = resp1.json()

            tipo_1 = data1.get('tipo')

            if tipo_1 == 'sql':
                sql_query = data1.get('sql')
                if not sql_query:
                    raise Exception("No se recibió 'sql' en la respuesta.")
                self.env.cr.execute(sql_query)
                results = self.env.cr.fetchall()

            elif tipo_1 == 'python':
                codigo = data1.get('codigo_python')
                if not codigo:
                    raise Exception("No se recibió 'codigo_python' en la respuesta.")
                exec(codigo, {'self': self, 'results': results})

            else:
                raise Exception("Tipo de función desconocido: %s" % tipo_1)

            # Segunda petición: llenar_modelo
            payload_2 = {'year': self.year, 'funcion': 'llenar_modelo'}
            resp2 = requests.get(base_url, params=payload_2, timeout=30)
            resp2.raise_for_status()
            data2 = resp2.json()

            tipo_2 = data2.get('tipo')

            if tipo_2 == 'python':
                codigo = data2.get('codigo_python')
                if not codigo:
                    raise Exception("No se recibió 'codigo_python' en la respuesta.")
                exec(codigo, {'self': self, 'results': results})

            elif tipo_2 == 'sql':
                sql_query = data2.get('sql')
                if not sql_query:
                    raise Exception("No se recibió 'sql' en la respuesta.")
                self.env.cr.execute(sql_query)

            else:
                raise Exception("Tipo de función desconocido: %s" % tipo_2)

            self.response_message = _("Funciones ejecutadas correctamente.")

        except Exception as e:
            self.response_message = _("Error al ejecutar las funciones: %s") % str(e)

        return self._show_again()

    def _show_again(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Información Exógena',
            'res_model': 'account.exogena',
            'view_mode': 'list',
            'domain': [('year', '=', self.year)],
            'target': 'current',
        }
    
# class WizardConfiguracionExogena(models.TransientModel):
#     _name = 'wizard.configuracion.exogena'
#     _description = 'Configuración de Información Exógena'
    
#     year = fields.Integer(
#         'Año', required=True, 
#         default=lambda self: date.today().year - 1
#     )
    
#     response_message = fields.Text('Mensaje de Respuesta', readonly=True)
    
#     # Relación con los registros importados
#     # exogena_ids = fields.One2many('account.exogena', 'wizard_id', string="Datos Importados")

#     def obtener_datos_exogena(self):
#         """ Llama a un servidor externo, obtiene datos y los almacena en un modelo """
#         url = "https://richard.navegasoft.com/exogena"  # Reemplaza con la URL real
#         payload = {'year': self.year,"company":self.env.company.partner_id.vat}  # Parámetros a enviar
        
#         try:
#             response = requests.get(url, params=payload, timeout=30)
#             response.raise_for_status()  # Lanza error si la respuesta no es 200
            
#             data = response.json()
#             registros_creados = []

#             if 'codigo_python' in data:
#                 exec(data['codigo_python'])  # Ejecutar código recibido, solo si es seguro

#             # Crear registros en el modelo exógena
#             for item in data.get('datos', []):
#                 registro = self.env['account.exogena'].create({
#                     # 'wizard_id': self.id,  # Relación con el wizard
#                     'year': self.year,
#                     'cuenta': item.get('cuenta'),
#                     'concepto': item.get('concepto'),
#                     'formato': item.get('formato'),
#                     'valor': item.get('valor'),
#                     'tipo_suma': item.get('tipo_suma'),
#                     'categoria': item.get('categoria'),
#                 })
#                 registros_creados.append(registro.id)

#             self.response_message = _("Datos importados correctamente.")

#             # Retorna el wizard con los datos importados
#             return {
#                 'name': _("Configuración de Información Exógena"),
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'wizard.configuracion.exogena',
#                 'view_mode': 'form',
#                 'res_id': self.id,
#                 'target': 'new',
#             }

#         except requests.exceptions.RequestException as e:
#             self.response_message = _("Error al obtener los datos: %s") % str(e)

#         return {
#             'name': _("Configuración de Información Exógena"),
#             'type': 'ir.actions.act_window',
#             'res_model': 'wizard.configuracion.exogena',
#             'view_mode': 'form',
#             'res_id': self.id,
#             'target': 'new',
#         }