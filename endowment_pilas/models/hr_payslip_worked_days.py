class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    pila_include_days = fields.Boolean(
        string='Incluir días en total PILA',
        default=True,
        help=(
            'Si está activo, los días de esta línea se sumarán al total '
            'de días laborados del archivo Excel PILA.'
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        work_entry_type_model = self.env['hr.work.entry.type']

        for vals in vals_list:
            if 'pila_include_days' not in vals:
                work_entry_type_id = vals.get('work_entry_type_id')

                if work_entry_type_id:
                    work_entry_type = work_entry_type_model.browse(
                        work_entry_type_id
                    )
                    vals['pila_include_days'] = (
                        work_entry_type.pila_include_days
                    )

        return super().create(vals_list)