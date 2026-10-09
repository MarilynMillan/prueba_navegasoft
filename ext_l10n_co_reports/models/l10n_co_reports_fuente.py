# -*- coding: utf-8 -*-

from odoo import models

class FuenteReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_co.fuente.report.handler'
    
    def _get_domain(self, report, options, line_dict_id=None):
        domain = super()._get_domain(report, options, line_dict_id=line_dict_id)
        
        # Remove filter by code
        domain.remove(('account_id.code', '=like', '2365%'))
        domain.remove(('account_id.code', '!=', '236505'))
        
        # Add filter by tax value
        domain.append(('tax_line_id.l10n_co_edi_type.name', '=', 'ReteRenta'))
        return domain