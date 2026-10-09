# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api

class ResCity(models.Model):
    _inherit = 'res.city'

    name = fields.Char(translate=False)
    code = fields.Char(string="Code")
    postal_code = fields.Char(string=u'Postal code',)

    def name_get(self):
        rec = []
        for recs in self:
            name = '%s / %s [%s]' % (recs.name or '', recs.state_id.name or '', recs.code or '')
            rec += [ (recs.id, name) ]
        return rec

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Se hereda metodo name search y se sobreescribe para hacer la busqueda 
        por el codigo de la ciudad
        """
        if not args:
            args = []
        args = args[:]
        ids = []
        if name:
            ids = self.search([('code', '=like', name + "%")] + args, limit=limit)
            if not ids:
                ids = self.search([('name', operator, name)] + args,limit=limit)
        else:
            ids = self.search(args, limit=100)

        if ids:
            return ids.name_get()
        return self.name_get()