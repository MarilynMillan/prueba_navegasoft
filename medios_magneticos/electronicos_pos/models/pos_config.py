# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError

class pos_config(models.Model):
    _inherit = "pos.config"

    valor_uvt = fields.Integer('Valor maximo UVs', default=212060,help='Se comprueba si el diario es de facturas electronicas',)

    @api.model
    def load_fields(self):
        fields = super(pos_config, self).load_fields()
        fields.append('uvt_value')
        return fields
    
    def restrictions_uvts(self):
        #restringir el valor de los uvts
        #if self.valor_uvt > 212060:
        print("VALOR DE EL OBJETO ANTES DE VALIDAR")
        print(self)
        return {'warning': {'title': _('Warning'),'message': _('My warning message.')}}
        raise UserError('''Hola, Te recordamos que, de acuerdo con las normativas tributarias, estás obligado a emitir factura electrónica después de haber alcanzado el monto de 5 UVTs, lo cual equivale a $212.060. Por lo tanto, te sugerimos completar la operación correspondiente utilizando una factura electrónica.       
        No dudes en comunicarte con nosotros si necesitas más información o asistencia en el proceso de emisión de la factura.''')



    # receipt = fields.Char("Receipt")
    # pos_reference = fields.Char("Reference")
    # receipt_type = fields.Selection(
    #     [("xml", "XML"), ("ticket", "Ticket")], "Receipt Type"
    # )

    
        

# class electronicos_pos(models.Model):
#     _name = 'electronicos_pos.electronicos_pos'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100