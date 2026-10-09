# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api, fields, models, _
# from odoo.exceptions import Warning


class WkWizardMessage(models.TransientModel):
	_name = "wk.wizard.message"
	_description = "Message Wizard"

	text = fields.Text(string='Message 1')
	text2 = fields.Text(string='Message 2')
	
	@api.model
	def genrated_message(self,message,name='Message/Summary',link='http://navegasoft.com'):
		res = self.create({'text':message,'text2':link})
		return {
			'name'     : name,
			'type'     : 'ir.actions.act_window',
			'res_model': 'wk.wizard.message',
			'view_mode': 'form',
			'target'   : 'new',
			'res_id'   : res.id,
		}
