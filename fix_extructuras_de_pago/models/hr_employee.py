# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class administradoras_colaborador(models.Model):
    _inherit = 'hr.employee'
    _description = 'contacto'

    employee_address_home = fields.Many2one('res.partner', string='Contacto',check_company=True)
    # def __init__(self):
    #   #  Override of __init__ to add access rights on new_field.             
    #   #  Access rights are disabled by default, but allowed            
    #   #  on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.  
    #   init_res = super(administradoras_colaborador, self).__init__(self)        
    #   # duplicate list to avoid modifying the original reference        
    #   type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)        
    #   type(self).SELF_WRITEABLE_FIELDS.extend(['employee_address_home'])        
    #   # duplicate list to avoid modifying the original reference        
    #   type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)        
    #   type(self).SELF_READABLE_FIELDS.extend(['employee_address_home'])        
    #   return init_res
    # name = fields.Char(string="Centro de costos")
    # company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    #administradoras_ids = fields.Many2many("hr.administradoras", string="Administradoras",domain="[('colaborador', '=', True),('centro_costos', '=', False)]") ##('ccostos.id', '=', department_id.id),


class administradoras_colaborador_user(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'contacto'

    employee_address_home = fields.Many2one('res.partner', string='Contacto')
    