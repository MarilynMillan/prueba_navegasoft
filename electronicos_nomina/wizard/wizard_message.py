##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WkWizardMessage(models.TransientModel):
	_name = "wk.wizard.message2"
	_description = "Message Wizard2"

	#@api.multi
	def button_generar_nota(self):
		ids_actual = self.env.context.get('active_ids', [])
		print(ids_actual)
		Payslip = self.env['hr.payslip'].browse(ids_actual[0])

		for payslip in Payslip:
			# copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
			copied_payslip = payslip.compute_refund(self.text,self.tipo)
			# copied_payslip.action_payslip_done()
		formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
		treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
		return {
            'name': ("Refund Payslip"),
            'view_mode': 'list, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'list'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }
		return  #self._export(report_type)
	
	
	text = fields.Text(string='Causa')
	tipo = fields.Selection([('Eliminar', 'Eliminar'),
                                    ('Modificar', 'Modificar')],
                                   string='Tipo de nota',
                                   required=True,
                                   default='Eliminar')

	@api.model
	def genrated_message(self,message,name='Message/Summary'):
		res = self.create({'text': message})
		return {
			'name'     : name,
			'type'     : 'ir.actions.act_window',
			'res_model': 'wk.wizard.message2',
			'view_mode': 'form',
			'target'   : 'new',
			'res_id'   : res.id,
		}

