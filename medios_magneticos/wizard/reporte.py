from odoo import models
from odoo.tools.sql import SQL

class CustomAccountReportHandler(models.AbstractModel):
    _name = 'l10n_co.custom.account.report.handler'
    _inherit = 'l10n_co.report.handler'
    _description = 'Custom Account Report Handler'

    def _get_query_results(self, report, options, domain, bimestre=False):
        queries = []
        # Se separa la consulta según los grupos de columnas (igual que en el reporte ICA)
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            # Se obtiene la consulta base utilizando el método del reporte contable
            query = report._get_report_query(column_group_options, 'strict_range', domain=domain)

            # Se realiza un LEFT JOIN a account_account para obtener los datos de la cuenta
            account_alias = query.left_join(
                lhs_alias='account_move_line',
                lhs_column='account_id',
                rhs_table='account_account',
                rhs_column='id',
                link='account_id'
            )
            # Si es necesario, también se puede unir account_move para filtrar por estado
            move_alias = query.left_join(
                lhs_alias='account_move_line',
                lhs_column='move_id',
                rhs_table='account_move',
                rhs_column='id',
                link='move_id'
            )
            # Se agrega una condición sobre el estado del asiento
            query.add_where("%s.state NOT IN ('draft', 'cancel')" % (move_alias))

            # Se obtienen de forma segura los campos "code" y "name" usando _field_to_sql
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name', query)

            # Se agregan estos campos a la SELECT
            query.add_select(account_code, 'codigo_cuenta')
            query.add_select(account_name, 'nombre_cuenta')
            # Se agregan los totales de débito y crédito
            query.add_select(SQL('SUM(account_move_line.debit)'), 'total_debito')
            query.add_select(SQL('SUM(account_move_line.credit)'), 'total_credito')

            # Se agrupan los resultados según los campos de cuenta
            query.add_group_by(account_code)
            query.add_group_by(account_name)

            # Si necesitas agrupar por bimestre, puedes agregarlo aquí (opcional)
            if bimestre:
                bimestre_expression = SQL('FLOOR((EXTRACT(MONTH FROM account_move_line.date) + 1) / 2)')
                query.add_select(bimestre_expression, 'bimestre')
                query.add_group_by(bimestre_expression)

            queries.append(query.select())

        # Se unen las consultas generadas y se ejecuta
        self._cr.execute(SQL(' UNION ALL ').join(queries))
        return self._cr.dictfetchall()

    def _get_domain(self, report, options, line_dict_id=None):
        # Puedes agregar condiciones adicionales al dominio (por ejemplo, filtrar por un código de cuenta)
        domain = super(CustomAccountReportHandler, self)._get_domain(report, options, line_dict_id=line_dict_id)
        # Ejemplo: filtrar las cuentas que comiencen con '2368'
        domain += [('account_id.code', '=like', '2368%')]
        return domain

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        domain = self._get_domain(report, options)
        query_results = self._get_query_results(report, options, domain)
        # Utiliza el método _get_partner_values del handler base para procesar los resultados
        return super(CustomAccountReportHandler, self)._get_partner_values(report, options, query_results, '_report_expand_unfoldable_line_custom')