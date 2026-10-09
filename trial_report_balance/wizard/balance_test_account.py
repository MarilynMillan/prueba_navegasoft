import xlsxwriter
import io
import base64
from collections import defaultdict

import locale
locale.setlocale(locale.LC_TIME, "es_ES.utf8")

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import SQL

COLUMNS = {
    'partner': {
        'select_column': " code_account, name_account, vat_partner, name_partner, inicial_amount, debit, credit, total ",
        'file_column': ['Código Cuenta Contable','Nombre Cuenta Contable','Identificación','Nombre Tercero','Saldo Inicial','Movimiento Débito','Movimiento Crédito','Saldo Final'],
        'size_column': [25,75,15,25,20,20,20,20]
    },
    'general': {
        'select_column': " code_account, name_account, inicial_amount, debit, credit, total",
        'file_column': ['Código Cuenta Contable','Nombre Cuenta Contable','Saldo Inicial','Movimiento Débito','Movimiento Crédito','Saldo Final'],
        'size_column': [25,75,20,20,20,20]
    }
}

class BalanceTestAccount(models.Model):
    _name = 'balance.test.account'
    _description = 'Balance de Pruebas'

    report_type = fields.Selection([
        ('partner','Balance de prueba por tercero'),
        ('general','Balance de pruebas general')
        ], string="Tipo de Informe", default="partner", required=True)
    
    view_type = fields.Selection([
        ('excel','Excel'),
        ('view','Vista'),
    ], default="excel", string="Presentación")
    
    date_start = fields.Date(string="Fecha Inicio",default=fields.Date.today())
    date_end = fields.Date(string="Fecha Final",default=fields.Date.today())
    
    account_account_ids = fields.Many2many("account.account",string="Cuentas")
    partner_ids = fields.Many2many("res.partner",string="Terceros")
    
    def _get_trial_balance_options(self, balance_report):
        options = balance_report.get_options({})
        options["date"]["period_type"] = "fiscalyear"
        options["date"]["filter"] = "custom"
        options["date"]["date_from"] = self.date_start
        options["date"]["date_to"] = self.date_end
        options["unfold_all"] = True
        return balance_report.get_options(options)

    def _query_third_party_sums(self, balance_report, options, account_account_ids=(), partner_ids=()):
        """Return grouped sums by (account_id, partner_id) with the same date logic as account_reports."""
        domain = []
        if account_account_ids:
            domain.append(("account_id", "in", list(account_account_ids)))
        if partner_ids:
            domain.append(("partner_id", "in", list(partner_ids)))

        sums_by_account_partner = defaultdict(lambda: {
            "initial_amount": 0.0,
            "debit": 0.0,
            "credit": 0.0,
        })

        gl_handler = self.env["account.general.ledger.report.handler"]
        initial_options = gl_handler._get_options_initial_balance(options)
        initial_domain = list(domain)
        if initial_options.get("include_current_year_in_unaff_earnings"):
            # Keep third-party initial balance aligned with Trial Balance/GL behavior at fiscal year start.
            initial_domain.append(("account_id.include_initial_balance", "=", True))

        initial_query = balance_report._get_report_query(initial_options, "from_beginning", domain=initial_domain)
        self._cr.execute(SQL(
            """
            SELECT
                account_move_line.account_id AS account_id,
                account_move_line.partner_id AS partner_id,
                SUM(%(balance_select)s) AS initial_amount
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            GROUP BY account_move_line.account_id, account_move_line.partner_id
            """,
            balance_select=balance_report._currency_table_apply_rate(SQL("account_move_line.balance")),
            table_references=initial_query.from_clause,
            currency_table_join=balance_report._currency_table_aml_join(initial_options),
            search_condition=initial_query.where_clause,
        ))
        for row in self._cr.dictfetchall():
            key = (row["account_id"], row["partner_id"])
            sums_by_account_partner[key]["initial_amount"] = row["initial_amount"] or 0.0

        period_query = balance_report._get_report_query(options, "strict_range", domain=domain)
        self._cr.execute(SQL(
            """
            SELECT
                account_move_line.account_id AS account_id,
                account_move_line.partner_id AS partner_id,
                SUM(%(debit_select)s) AS debit,
                SUM(%(credit_select)s) AS credit
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            GROUP BY account_move_line.account_id, account_move_line.partner_id
            """,
            debit_select=balance_report._currency_table_apply_rate(SQL("account_move_line.debit")),
            credit_select=balance_report._currency_table_apply_rate(SQL("account_move_line.credit")),
            table_references=period_query.from_clause,
            currency_table_join=balance_report._currency_table_aml_join(options),
            search_condition=period_query.where_clause,
        ))
        for row in self._cr.dictfetchall():
            key = (row["account_id"], row["partner_id"])
            sums_by_account_partner[key]["debit"] = row["debit"] or 0.0
            sums_by_account_partner[key]["credit"] = row["credit"] or 0.0

        return sums_by_account_partner
    
    def sql_select_view_all(self):
        return """ select {select_column} from balance_test_account_{table} ORDER BY id ASC""".format(select_column=COLUMNS[self.report_type]['select_column'],table=self.report_type)
    
    def sql_select_view(self):
        return """ select id from balance_test_account_{table} ORDER BY id ASC""".format(table=self.report_type)

    def _search_data_move_line_general(self):
        balance_report = self.env.ref("account_reports.trial_balance_report")
        options = self._get_trial_balance_options(balance_report)
        account_account_ids = []
        
        if self.account_account_ids:
            account_account_ids = tuple(self.account_account_ids.ids)

        lines = balance_report.with_context(from_trial_balance=True, account_account_ids=account_account_ids)._get_lines(options)
        self._cr.execute("DELETE FROM balance_test_account_general")
        
        for line in lines:
            name_code = line.get("name","").split(maxsplit=1) or ['','']
            code =  name_code[0] if name_code and len(name_code) > 0 else ''
            name =  name_code[1] if name_code and len(name_code) > 1 else ''
            initial_amount = line.get("columns",[{}])[0].get("no_format",0) - line.get("columns",[{}])[1].get("no_format",0) 
            debit = line.get("columns",[{}])[2].get("no_format",0) 
            credit = line.get("columns",[{}])[3].get("no_format",0) 
            total = line.get("columns",[{}])[4].get("no_format",0) - line.get("columns",[{}])[5].get("no_format",0) 
            
            if code == "Total":
                continue
            
            self.env.cr.execute("""
                    INSERT INTO balance_test_account_general(code_account, name_account, inicial_amount, debit, credit, total)
                    VALUES (%s,%s,%s,%s,%s,%s)
            """, (code, name, initial_amount, debit, credit, total))
            
        return True
    
    def _search_data_move_line_third_party(self):
        balance_report = self.env.ref("account_reports.trial_balance_report")
        options = self._get_trial_balance_options(balance_report)
        account_account_ids = []
        partner_ids = []
        
        if self.account_account_ids:
            account_account_ids = tuple(self.account_account_ids.ids)
        
        if self.partner_ids:
            partner_ids = tuple(self.partner_ids.ids)
        
        lines = balance_report.with_context(
            from_trial_balance=True,
            account_account_ids=account_account_ids,
            partner_ids=partner_ids,
        )._get_lines(options)
        self._cr.execute("DELETE FROM balance_test_account_partner")

        third_party_sums = self._query_third_party_sums(
            balance_report,
            options,
            account_account_ids=account_account_ids,
            partner_ids=partner_ids,
        )
        third_party_sums_by_account = defaultdict(list)
        for (grouped_account_id, grouped_partner_id), grouped_values in third_party_sums.items():
            third_party_sums_by_account[grouped_account_id].append((grouped_partner_id, grouped_values))

        partner_map = {}
        partner_record_ids = {partner_id for _, partner_id in third_party_sums.keys() if partner_id}
        if partner_record_ids:
            partner_map = {
                partner["id"]: partner
                for partner in self.env["res.partner"].browse(list(partner_record_ids)).read(["vat", "name"])
            }

        currency = self.env.company.currency_id
        final_lines = []
        for line in lines:
            model_name, account_id = balance_report._get_model_info_from_id(line["id"])
            if model_name != "account.account":
                continue

            name_code = line.get("name", "").split(maxsplit=1) or ["", ""]
            code = name_code[0] if name_code and len(name_code) > 0 else ''

            if code == "Total":
                continue

            name = name_code[1] if name_code and len(name_code) > 1 else ''
            initial_amount = line.get("columns", [{}])[0].get("no_format", 0) - line.get("columns", [{}])[1].get("no_format", 0)
            debit = line.get("columns", [{}])[2].get("no_format", 0)
            credit = line.get("columns", [{}])[3].get("no_format", 0)
            total = line.get("columns", [{}])[4].get("no_format", 0) - line.get("columns", [{}])[5].get("no_format", 0)

            final_lines.append({
                'code': code,
                'name': name,
                'initial_amount': initial_amount,
                'debit': debit,
                'credit': credit,
                'total': total,
                'vat_partner': '',
                'name_partner': '',
                'third_party': False
            })

            # If the account summary is fully zero, keep third-party section empty for this account.
            if (
                currency.is_zero(initial_amount)
                and currency.is_zero(debit)
                and currency.is_zero(credit)
                and currency.is_zero(total)
            ):
                continue

            account_partner_rows = []
            for grouped_partner_id, grouped_values in third_party_sums_by_account.get(account_id, []):
                partner_data = partner_map.get(grouped_partner_id, {})
                partner_vat = partner_data.get("vat") or "NINGUNO"
                partner_name = partner_data.get("name") or "NINGUNO"
                line_initial = grouped_values["initial_amount"]
                line_debit = grouped_values["debit"]
                line_credit = grouped_values["credit"]
                line_total = line_initial + line_debit - line_credit

                if (
                    currency.is_zero(line_initial)
                    and currency.is_zero(line_debit)
                    and currency.is_zero(line_credit)
                    and currency.is_zero(line_total)
                ):
                    continue

                account_partner_rows.append({
                    "code": code,
                    "name": name,
                    "vat_partner": partner_vat,
                    "name_partner": partner_name,
                    "initial_amount": line_initial,
                    "debit": line_debit,
                    "credit": line_credit,
                    "total": line_total,
                    "third_party": True,
                })

            account_partner_rows.sort(key=lambda row: (row["vat_partner"], row["name_partner"]))
            sum_initial = sum(row["initial_amount"] for row in account_partner_rows)
            sum_debit = sum(row["debit"] for row in account_partner_rows)
            sum_credit = sum(row["credit"] for row in account_partner_rows)
            sum_total = sum(row["total"] for row in account_partner_rows)

            diff_initial = initial_amount - sum_initial
            diff_debit = debit - sum_debit
            diff_credit = credit - sum_credit
            diff_total = total - sum_total

            if (
                not currency.is_zero(diff_initial)
                or not currency.is_zero(diff_debit)
                or not currency.is_zero(diff_credit)
                or not currency.is_zero(diff_total)
            ):
                account_partner_rows.append({
                    "code": code,
                    "name": name,
                    "vat_partner": "NINGUNO",
                    "name_partner": "NINGUNO",
                    "initial_amount": diff_initial,
                    "debit": diff_debit,
                    "credit": diff_credit,
                    "total": diff_total,
                    "third_party": True,
                })

            for third_party_line in account_partner_rows:
                final_lines.append({
                    'code': code,
                    'name': name,
                    'vat_partner': third_party_line["vat_partner"],
                    'name_partner': third_party_line["name_partner"],
                    'initial_amount': third_party_line["initial_amount"],
                    'debit': third_party_line["debit"],
                    'credit': third_party_line["credit"],
                    'total': third_party_line["total"],
                    'third_party': True
                })
        
        # Insert final data
        for line in final_lines:
            self.env.cr.execute("""
                INSERT INTO balance_test_account_partner(code_account, name_account, vat_partner, name_partner, third_party, inicial_amount, debit, credit, total)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (line['code'], line['name'], line['vat_partner'], line['name_partner'], line['third_party'], line['initial_amount'], line['debit'], line['credit'], line['total']))
            
        return True
    
    def generate_report(self):
        if self.view_type == "excel":
            if self.report_type == "general":
                self._search_data_move_line_general()
            else:
                self._search_data_move_line_third_party()
            
            self._cr.execute(self.sql_select_view_all())
            data = self._cr.fetchall()
            attachment_id = self.generate_report_excel(data)
            base_url = self.env["ir.config_parameter"].get_param("web.base.url")
            body_url = "%s/web/content/%s?download=true" %(base_url,attachment_id) 
            return {
                "type": "ir.actions.act_url",
                "url": body_url,
                "target": "current",
            }
        else:
            if self.report_type == "general":
                self._search_data_move_line_general()
            else:
                self._search_data_move_line_third_party()
                
            self._cr.execute(self.sql_select_view())
            data = self._cr.fetchall()
            data = [i[0] for i in data] if data else []
            view_id = self.env.ref('trial_report_balance.balance_test_account_{table}_view_tree'.format(table=self.report_type)).id
            
            return {
                'name': 'Balance de prueba por tercero'.upper() if self.report_type == 'partner' else 'Balance de pruebas general'.upper(),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,pivot',
                'views': [(view_id, 'list'),(False, 'pivot')],
                'res_model': "balance.test.account.{table}".format(table=self.report_type),
                'domain': [('id','in',data)],
                'target': 'current',
                'context': {'create': False},
            }
    
    def generate_report_excel(self,data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': False})
        worksheet = workbook.add_worksheet('Hoja1')
        header_format = workbook.add_format({'bold':True,'fg_color':'#00AAFF','font_size':30,'color':'white','align':'center'})
        header_name = 'Balance de prueba por tercero' if self.report_type == 'partner' else 'Balance de pruebas general'
        file_name = '%s.xlsx'%(header_name)
        worksheet.merge_range('A1:%s1'%(chr(len(COLUMNS[self.report_type]['file_column'])+64)),header_name.upper(),header_format)
        subheader_format = workbook.add_format({'bold':True,'fg_color':'#00AAFF','font_size':14,'color':'white','align':'center'})
        subheader_name = 'De %s %s a %s %s'%(self.date_start.strftime("%B").capitalize(),self.date_start.strftime("%Y"),self.date_end.strftime("%B").capitalize(),self.date_end.strftime("%Y"))
        worksheet.merge_range('A2:%s2'%(chr(len(COLUMNS[self.report_type]['file_column'])+64)),subheader_name,subheader_format)
        tableheader_format = workbook.add_format({'bold':True,'fg_color':'#F1F4F9','font_size':12,'align':'center'})
        worksheet.write_row('A3',COLUMNS[self.report_type]['file_column'],tableheader_format)
        row = 3
        col = 0
        cell_format = False
        for i in data:
            col = 0
            for c in i:
                if isinstance(c,float):
                    cell_format = workbook.add_format({'num_format': '#,##0.00'})
                if cell_format:
                    worksheet.write(row,col,c,cell_format)
                else:
                    worksheet.write(row,col,c)
                cell_format = False
                col += 1
            row += 1
        
        for x,j in enumerate(COLUMNS[self.report_type]['size_column']):
            worksheet.set_column(x,x,j)
        workbook.close()
        output.seek(0)
        self.env["ir.attachment"].search([('name','=',file_name)]).unlink()
        attachement_id = self.env["ir.attachment"].create({
            'name': file_name,
            'datas': base64.encodebytes(output.getvalue()),
            'res_model': 'balance.test.account',
            'res_id': self.id
        })
        output.close()
        return attachement_id.id


        

class BalanceTestAccountPartner(models.Model):
    _name = 'balance.test.account.partner'
    _description = 'Balance de Pruebas Tercero'
    
    third_party = fields.Boolean(default=False)
    code_account = fields.Char("Código Cuenta Contable")
    name_account = fields.Char("Nombre Cuenta Contable")
    vat_partner = fields.Char("Identificacion")
    name_partner = fields.Char("Nombre Tercero")
    inicial_amount = fields.Float("Saldo Inicial")
    debit = fields.Float("Debito")
    credit = fields.Float("Credito")
    total = fields.Float("Saldo Final")

class BalanceTestAccountGeneral(models.Model):
    _name = 'balance.test.account.general'
    _description = 'Balance de Pruebas General'

    code_account = fields.Char("Código Cuenta Contable")
    name_account = fields.Char("Nombre Cuenta Contable")
    inicial_amount = fields.Float("Saldo Inicial")
    debit = fields.Float("Debito")
    credit = fields.Float("Credito")
    total = fields.Float("Saldo Final")
