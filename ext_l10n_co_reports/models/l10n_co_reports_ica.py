# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import models
from odoo.tools.sql import SQL


class ICAReportCustomHandler(models.AbstractModel):
    _inherit = "l10n_co.ica.report.handler"

    # ---------------------------------------------------------
    # Domain
    # ---------------------------------------------------------
    def _get_domain(self, report, options, line_dict_id=None):
        domain = super()._get_domain(report, options, line_dict_id=line_dict_id)

        # Remove filter by code (si no existe, no revientes)
        try:
            domain.remove(("account_id.code", "=like", "2368%"))
        except ValueError:
            pass

        # Add filter by tax value
        domain.append(("tax_line_id.l10n_co_edi_type.name", "=", "ReteICA"))
        return domain

    # ---------------------------------------------------------
    # Query (partner + account + optional bimestre)
    # ---------------------------------------------------------
    def _get_query_results(self, report, options, domain, bimestre=False):
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, "strict_range", domain=domain)

            # Bimestre opcional
            bimestre_expression = SQL("FLOOR((EXTRACT(MONTH FROM account_move_line.date) + 1) / 2)")
            bimestre_column = SQL("%s AS bimestre,", bimestre_expression) if bimestre else SQL()
            bimestre_groupby = SQL(", %s", bimestre_expression) if bimestre else SQL()
            bimestre_orderby = SQL(", %s", bimestre_expression) if bimestre else SQL()

            # Cuenta SIEMPRE (estilo nativo)
            account_alias = query.left_join(
                lhs_alias="account_move_line",
                lhs_column="account_id",
                rhs_table="account_account",
                rhs_column="id",
                link="account_id",
            )
            account_code = self.env["account.account"]._field_to_sql(account_alias, "code", query)
            account_name = self.env["account.account"]._field_to_sql(account_alias, "name", query)
            account_id = SQL.identifier(account_alias, "id")

            account_name_select = SQL("%s || ' ' || (%s) AS account_name,", account_code, account_name)
            account_id_select = SQL("%s AS account_id,", account_id)
            group_by_account = SQL(", %s", account_id)

            # Base imponible con tu lógica
            tax_base_amount_select = SQL("""
                SUM(CASE
                    WHEN account_move_line.credit > 0
                        THEN account_move_line.tax_base_amount
                    WHEN account_move_line.debit > 0
                        THEN account_move_line.tax_base_amount * -1
                    ELSE 0
                END)
            """)

            # No traer cuentas en 0
            having_clause = SQL("HAVING %s != 0", tax_base_amount_select)

            queries.append(
                SQL(
                    """
                    SELECT
                        %(column_group_key)s AS column_group_key,
                        SUM(account_move_line.credit - account_move_line.debit) AS balance,
                        %(tax_base_amount_select)s AS tax_base_amount,
                        %(bimestre_column)s
                        %(account_name)s
                        %(account_id)s
                        rp.id AS partner_id,
                        rp.name AS partner_name
                    FROM %(table_references)s
                    JOIN res_partner rp ON account_move_line.partner_id = rp.id
                    WHERE %(search_condition)s
                    GROUP BY rp.id%(group_by_account)s%(bimestre_groupby)s
                    %(having_clause)s
                    ORDER BY rp.name, rp.id, account_name, account_id%(bimestre_orderby)s
                    """,
                    column_group_key=column_group_key,
                    tax_base_amount_select=tax_base_amount_select,
                    bimestre_column=bimestre_column,
                    account_name=account_name_select,
                    account_id=account_id_select,
                    table_references=query.from_clause,
                    search_condition=query.where_clause,
                    group_by_account=group_by_account,
                    bimestre_groupby=bimestre_groupby,
                    having_clause=having_clause,
                    bimestre_orderby=bimestre_orderby,
                )
            )

        self._cr.execute(SQL(" UNION ALL ").join(queries))
        return self._cr.dictfetchall()

    # ---------------------------------------------------------
    # Lines: Partner -> Account -> (optional) Bimestre
    # ---------------------------------------------------------
    def _get_lines(self, report, options, line_id=None):
        """
        Mantiene el reporte original, pero cambia el detalle:
        Agrupa por Partner, dentro por Cuenta (con nombre), y opcionalmente por Bimestre.
        """
        # Si el reporte base usa line_id para "unfold", delegamos al super para no romper flows
        # PERO si quieres que el unfold sea el nuestro, puedes comentar esto.
        # (Normalmente funciona bien sin depender del super.)
        # if line_id:
        #     return super()._get_lines(report, options, line_id=line_id)

        domain = self._get_domain(report, options, line_dict_id=None)

        # Detectar si el reporte está configurado para bimestre (si tu base lo maneja por options)
        # Si ya sabes que siempre es bimestre, pon bimestre=True fijo.
        bimestre = bool(options.get("bimestre")) or bool(options.get("ica_bimestre")) or False

        results = self._get_query_results(report, options, domain, bimestre=bimestre)

        # Armado: (partner) -> (account) -> [rows...]
        grouped = defaultdict(lambda: defaultdict(list))
        for r in results:
            pkey = (r["partner_id"], r["partner_name"])
            akey = (r.get("account_id"), r.get("account_name"))
            grouped[pkey][akey].append(r)

        # Helpers para columnas
        column_groups = list(report._split_options_per_column_group(options).keys())

        def _blank_cols():
            return [{"name": ""} for _ in column_groups]

        def _cols_from_map(amount_by_cg):
            cols = []
            for cg in column_groups:
                val = amount_by_cg.get(cg, 0.0)
                cols.append({"name": report.format_value(val, figure_type="monetary", options=options)})
            return cols

        def _sum_map(rows, field_name):
            m = defaultdict(float)
            for rr in rows:
                m[rr["column_group_key"]] += float(rr.get(field_name) or 0.0)
            return m

        lines = []

        # Recorremos partners
        for (partner_id, partner_name), accounts_map in grouped.items():
            # Suma total del partner (suma de todas las cuentas)
            all_rows = [rr for acc_rows in accounts_map.values() for rr in acc_rows]
            partner_amounts = _sum_map(all_rows, "balance")  # o usa "tax_base_amount" si quieres base

            partner_line_id = report._get_generic_line_id("partner", partner_id)
            lines.append(
                {
                    "id": partner_line_id,
                    "name": partner_name or "",
                    "level": 1,
                    "unfoldable": True,
                    "unfolded": True,  # si quieres que salga abierto por defecto
                    "columns": _cols_from_map(partner_amounts),
                }
            )

            # Cuentas del partner
            for (account_id, account_name), acc_rows in accounts_map.items():
                acc_amounts = _sum_map(acc_rows, "balance")  # o "tax_base_amount"
                acc_line_id = report._get_generic_line_id("account", f"{partner_id}_{account_id}")

                lines.append(
                    {
                        "id": acc_line_id,
                        "name": account_name or "",
                        "parent_id": partner_line_id,
                        "level": 2,
                        "unfoldable": bool(bimestre),
                        "unfolded": True if bimestre else False,
                        "columns": _cols_from_map(acc_amounts),
                    }
                )

                # Bimestre (si aplica)
                if bimestre:
                    # Agrupar por bimestre
                    by_bim = defaultdict(list)
                    for rr in acc_rows:
                        by_bim[rr.get("bimestre")].append(rr)

                    for bim, bim_rows in sorted(by_bim.items(), key=lambda x: (x[0] is None, x[0])):
                        bim_amounts = _sum_map(bim_rows, "balance")  # o "tax_base_amount"
                        bim_line_id = report._get_generic_line_id("bimestre", f"{partner_id}_{account_id}_{bim}")

                        lines.append(
                            {
                                "id": bim_line_id,
                                "name": f"Bimestre {int(bim)}" if bim else "Bimestre",
                                "parent_id": acc_line_id,
                                "level": 3,
                                "columns": _cols_from_map(bim_amounts),
                            }
                        )

        return lines
