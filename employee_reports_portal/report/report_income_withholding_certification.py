from odoo import models, exceptions, api
import datetime

class IncomeWithholdingCertification(models.AbstractModel):
    _name = 'report.employee_reports_portal.iw_certification'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Sobreescritura del metodo para tener mediante sentencia SQL la DATA para generar el certificado
        de ingresos y retenciones."""
        
        #if self.env['hr.salary.rule'].search([('concept', '=', None)]):
        #    raise exceptions.ValidationError("Reglas salariales pendientes por asignar concepto.")

        if data['form']['certificate_year']:
            startdate = datetime.date(int(data['form']['certificate_year']), 1, 1)
            enddate = datetime.date(int(data['form']['certificate_year']), 12, 31)
            
            """Genera la información del empleado para la cabecera del reporte"""
            sql_statement = """
                SELECT par.name,			                                        -- Nombre empresa
                       par.vat, 					                                        -- Nit empresa
                       com.verification_code,		                                        -- Digito de verificacion de la compañia   			
                       CASE WHEN emp.type_document = 'rut' then '31'
                            WHEN emp.type_document = 'id_document' then '13' 
                            WHEN emp.type_document = 'id_card' then '12'
                            WHEN emp.type_document = 'passport' then '41'
                            WHEN emp.type_document = 'foreign_id_card' then '42'
                            WHEN emp.type_document = 'external_id' then '50'
                            WHEN emp.type_document = 'diplomatic_card' then ''
                            WHEN emp.type_document = 'residence_document' then '91'
                            WHEN emp.type_document = 'civil_registration' then '11'
                            WHEN emp.type_document = 'national_citizen_id' then '13'
                            ELSE 'n.d.'				                                        -- Tipo de documento empleado
                       END emp_documenttype, 
                       emp.identification_id,		                                        -- Numero de idetificación del empleado
                       emp."name" name_employee,	                                        -- Nombre del empleado
                       TO_DATE(%(startdate)s, 'YYYY-MM-DD') start_date,                     -- Fecha de inicio
                       TO_DATE(%(enddate)s, 'YYYY-MM-DD') end_date,			                -- Fecha final
                       current_date c_date,			                                        -- Fecha de expedicion
                       par.city,					                                        -- Ciudad
                       par.state_id,    		                                            -- Departamento
                       par.zip                                                              -- Código Ciudad 
                FROM res_company com
                     INNER JOIN res_partner par ON ( com.partner_id = par.id )
                     INNER JOIN hr_employee emp ON ( emp.company_id = com.id AND emp.id = %(employee_id)s)
                WHERE com.id = %(company_id)s"""

            self.env.cr.execute(sql_statement, {
                'startdate': str(startdate),
                'enddate': str(enddate),
                'employee_id': data['form']['employee_id'],
                'company_id': data['form']['company_id']
            })
            
            emp_data = self._cr.dictfetchall()
            
            """Genera la información agrupada por conceptos a imprimir en el certificado 
            para el empleado seleccionado"""
            sql_statement = """
                SELECT cpt.type,
                       cpt.code,
                       cpt."name", 
                       CAST (COALESCE(SUM(det.total), 0) as money) as value
                FROM hr_certified_concept cpt
                    INNER JOIN res_company com ON ( com.id = %(company_id)s )
                    LEFT JOIN hr_salary_rule rul ON ( rul.concept = cpt.id )
                    INNER JOIN hr_employee emp ON ( emp.company_id = com.id AND emp.id = %(employee_id)s)
                    LEFT JOIN hr_payslip pay ON ( emp.company_id = pay.company_id AND emp.id = pay.employee_id AND pay.state  = 'done' and
                                                    pay.date_from >= to_date(%(startdate)s, 'YYYY-MM-DD') AND 
                                                    pay.date_to <= to_date(%(enddate)s, 'YYYY-MM-DD') )
                      LEFT JOIN hr_payslip_line det ON ( pay.id = det.slip_id AND det.salary_rule_id = rul.id )
                WHERE cpt.is_print = True
                GROUP BY cpt.type, cpt.code, cpt.name
                ORDER BY cpt.code
            """

            self.env.cr.execute(sql_statement, {
                'startdate': str(startdate),
                'enddate': str(enddate),
                'employee_id': data['form']['employee_id'],
                'company_id': data['form']['company_id']    
            })
            
            cer_vals = self._cr.dictfetchall()
            
            """Genera totales por grupo de conceptos (Ingresos, Retenciones)"""
            sql_statement = """
                SELECT cpt.type,
                        CAST (COALESCE(SUM(det.total), 0) as money) as value
                FROM hr_certified_concept cpt
                        INNER JOIN res_company com ON ( com.id = %(company_id)s )
                        LEFT JOIN hr_salary_rule rul ON ( rul.concept = cpt.id )
                        INNER JOIN hr_employee emp ON ( emp.company_id = com.id AND emp.id = %(employee_id)s)
                        LEFT JOIN hr_payslip pay ON ( emp.company_id = pay.company_id AND emp.id = pay.employee_id AND pay.state  = 'done' and
                                                    pay.date_from >= to_date(%(startdate)s, 'YYYY-MM-DD') AND 
                                                    pay.date_to <= to_date(%(enddate)s, 'YYYY-MM-DD') )
                        LEFT JOIN hr_payslip_line det ON ( pay.id = det.slip_id AND det.salary_rule_id = rul.id )
                WHERE cpt.is_print = True
                GROUP BY cpt.type
                ORDER BY cpt.type
            """
            
            self.env.cr.execute(sql_statement, {
                'startdate': str(startdate),
                'enddate': str(enddate),
                'employee_id': data['form']['employee_id'],
                'company_id': data['form']['company_id'] 
            })
            
            cer_tota = self._cr.dictfetchall()
            
        else:
            raise exceptions.ValidationError("Por favor seleccione el período.")

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'company': self.env['res.company'].browse(data['form']['company_id']).sudo(),
            'year': data['form']['certificate_year'],
            'emp_data': emp_data,
            'cer_vals': cer_vals,
            'cer_tota': cer_tota
        }
