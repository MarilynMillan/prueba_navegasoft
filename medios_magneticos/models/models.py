
from odoo import models, fields, api
from lxml import etree    
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class ResCompany(models.Model):
    _inherit = 'res.company'

    medios_magneticos_platform_id = fields.Char(
        string='ID Plataforma Medios Magnéticos',
        help='Identificador usado por la integración externa de medios magnéticos.'
    )

class account_concepto(models.Model):
    _name = 'account.concepto'
    _description = 'Conceptos de medios magnéticos'

    name = fields.Char("Concepto")
    formato = fields.Char("Formato")
    tipo_monto = fields.Selection(
        [('Dialy','Diario'),
         ('weekly','Semanal'),
         ('Monthly','Mes'),
         ('Yearly','Año'),],
        'Tipo Monto')
    descripcion = fields.Char('Descripción')

class account_categoria(models.Model):
    _name = 'account.categoria'
    _description = 'Categorías de medios magnéticos'

    name = fields.Char("Categoría")
    formato = fields.Char("Formato")
    year = fields.Selection(
        [('2023','2023'),
         ('2024','2024'),
         ('2025','2025'),
         ('2026','2026'),
         ('2027','2027'),],
        'Año')

class account_asoconcepto(models.Model):
    _name = 'account.asoconcepto2'
    _description = 'Asociación de conceptos2'

    name = fields.Char('Nombre')
    year = fields.Selection(
        [('2023','2023'),
         ('2024','2024'),
         ('2025','2025'),
         ('2026','2026'),
         ('2027','2027'),],
        'Año')
    cuenta = fields.Many2one("account.account",required=True)
    concepto = fields.Many2one("account.concepto",required=True)
    formato = fields.Char('Formato',required=True)
    tipo_suma = fields.Selection(
        [('suma_debitos','1. Suma debitos'),
         ('suma_creditos','2. Suma creditos'),
         ('debitos_creditos','3. Debitos - creditos'),
         ('saldo_general','4. Saldo general'),
         ('saldo_inicial','5. Saldo inicial'),],
        'Tipo de suma',required=True)
    categoria = fields.Many2one('account.categoria',required=True)    
    fecha_expediccion = fields.Date('Fecha de expedición:')
    ciudad = fields.Many2one('res.country.state')
    tipo_de_fondo = fields.Char('Tipo de fondo')
    codigo_fondo = fields.Char('Código de fondo')
    ano_de_categoria = fields.Char("Año de categoría",compute='compute_display_name', store=True)

class account_asoconcepto(models.Model):
    _name = 'account.asoconcepto'
    _description = 'Asociación de conceptos'

    name = fields.Char('Nombre')
    year = fields.Selection(
        [('2023','2023'),
         ('2024','2024'),
         ('2025','2025'),
         ('2026','2026'),
         ('2027','2027'),],
        'Año')
    cuenta = fields.Many2one("account.account",required=True)
    concepto = fields.Many2one("account.concepto",required=True)
    formato = fields.Char('Formato',required=True)
    formaton = fields.Char('Formato número',required=True)
    tipo_suma = fields.Selection(
            [('suma_debitos','1. Suma débitos'),
             ('suma_creditos','2. Suma créditos'),
             ('debitos_creditos','3. Débitos - créditos'),
             ('saldo_general','4. Saldo general'),
             ('saldo_inicial','5. Saldo inicial'),],
            'Tipo de suma',required=True)
    categoria = fields.Many2one('account.categoria',required=True)    
    fecha_expediccion = fields.Date('Fecha de expediccion:')
    ciudad = fields.Many2one('res.country.state')
    tipo_de_fondo = fields.Char('Tipo de fondo')
    codigo_fondo = fields.Char('Código de fondo')
    ano_de_categoria = fields.Char("Año de categoría",compute='compute_display_name', store=True)



    @api.depends('categoria')
    def compute_display_name(self):
        # This will be called every time the name or surname field changes
        for concepto in self:
            concepto.ano_de_categoria = concepto.categoria.year
        # for ano in concepto.categoria:
        #     self.ano_de_categoria += ano.year
        #pass

    @api.onchange('concepto')
    def on_change_state(self):
        for record in self:
            if record.concepto:
                formatii = record.concepto.formato
                record.formato = record.concepto.descripcion +' ('+formatii+')'
                record.formaton = formatii
                res = {'domain': {'categoria': [('formato', '=', formatii)]}}
                print(res)
                return res
            else:
                record.formato = ' '
            #print self.state, self.lgs


class AccountExogenaConfig(models.Model):
    _name = 'account.exogena_config'
    _description = 'Configuración Unificada de Exógena'
    
    @staticmethod
    def _get_years_selection():
        current_year = datetime.now().year
        return [(str(y), str(y)) for y in range(current_year - 2, current_year + 6)]

    year = fields.Selection(selection=_get_years_selection(), string="Año", required=True)

    # Datos del Concepto
    concepto_nombre = fields.Char("Nombre del Concepto", required=True)
    concepto_descripcion = fields.Char("Descripción del Concepto")
    tipo_monto = fields.Selection(
        [('Dialy', 'Diario'),
         ('weekly', 'Semanal'),
         ('Monthly', 'Mensual'),
         ('Yearly', 'Anual')],
        'Tipo de Monto')

    # Datos de la Categoría
    categoria_nombre = fields.Char("Nombre de la Categoría", required=True)
    formato = fields.Char("Formato", required=True)
    

    # Asociación
    cuenta = fields.Many2one("account.account", required=True)
    tipo_suma = fields.Selection(
        [('suma_debitos','1. Suma débitos'),
         ('suma_creditos','2. Suma créditos'),
         ('debitos_creditos','3. Débitos - créditos'),
         ('saldo_general','4. Saldo general'),
         ('saldo_inicial','5. Saldo inicial')],
        'Tipo de suma',
        required=True)
    
    ciudad = fields.Many2one('res.country.state', string='Ciudad')
    fecha_expediccion = fields.Date('Fecha de Expedición')
    tipo_de_fondo = fields.Char('Tipo de Fondo')
    codigo_fondo = fields.Char('Código de Fondo')

    # Campos computados y auxiliares
    nombre_completo = fields.Char("Nombre completo", compute='_compute_nombre_completo', store=True)

    @api.depends('concepto_nombre', 'categoria_nombre', 'formato', 'year')
    def _compute_nombre_completo(self):
        for record in self:
            record.nombre_completo = f"{record.concepto_nombre} - {record.categoria_nombre} ({record.formato} - {record.year})"



class PartnerXlsx(models.AbstractModel):
    _name = 'report.medios_magneticos.report_name'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Reportes de medios magnéticos'

    def _safe_float(self, value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _get_dynamic_headers(self, formato, year):
        association_records = self.env['account.asoconcepto'].search([
            ('formaton', '=', formato),
            ('year', '=', str(year)),
        ])
        headers = []
        seen = set()
        for category_name in association_records.mapped('categoria.name'):
            if category_name and category_name not in seen:
                seen.add(category_name)
                headers.append(category_name)

        if headers:
            return headers

        config_records = self.env['account.exogena_config'].search([
            ('formato', '=', formato),
            ('year', '=', str(year)),
        ])
        for category_name in config_records.mapped('categoria_nombre'):
            if category_name and category_name not in seen:
                seen.add(category_name)
                headers.append(category_name)

        if headers:
            return headers

        categoria_records = self.env['account.categoria'].search([
            ('formato', '=', formato),
            ('year', '=', str(year)),
        ])
        return [categoria.name for categoria in categoria_records if categoria.name]

    def generate_xlsx_report(self, workbook, data, lines):
        
        head = workbook.add_format({'pattern':True,'bg_color': '#595959','font_color':'white','font_size': 14,'valign':'center','valign': 'vcenter','align': 'center',"border":2})
        titulo = workbook.add_format({'pattern':True,'font_color':'#FFFFFF','bg_color': '#595959','font_size': 12, 'valign': 'center','valign': 'vcenter','align': 'center',"border":2})
        titulo.set_text_wrap()
        celda = workbook.add_format({"border":1})
        centrado = workbook.add_format({"border":1,'valign': 'center','valign': 'vcenter','align': 'center'})
        currency_format = workbook.add_format({'num_format': '$#,##0.00',"border":1,'valign':'center'})
        format_percent = workbook.add_format({'num_format': '0.00"%"',"border":1,'valign':'center'})
        sheet = workbook.add_worksheet('ARCHIVO DEUDA')

        sheet.set_column('A:Z', 20)

        sheet.write('A1', 'Concepto', titulo)
        sheet.write('B1', 'Tipo de documento', titulo)
        sheet.write('C1', 'Número de identificación del informado', titulo)
        sheet.write('D1', 'Primer Apellido', titulo)
        sheet.write('E1', 'Segundo Apellido', titulo)
        sheet.write('F1', 'Primer Nombre', titulo)
        sheet.write('G1', 'Otros Nombres', titulo)
        sheet.write('H1', 'Razón Social', titulo)
        sheet.write('I1', 'Dirección', titulo)
        # sheet.write('K3', 'PAGADO IVA', titulo)
        # sheet.write('K3', 'TOTAL PAGADO', titulo)
        sheet.write('J1', 'Cod. Dpto.', titulo)
        sheet.write('K1', 'Cod. Mcipio.', titulo)
        sheet.write('L1', 'País de residencia o domicilio', titulo)
        
        ##TITULOS DINAMICOS
        datos = lines or self.env['account.medios_magneticos'].search([])
        # for i in range(0, len(lines)):
        #for i in range(0, 16):
        if datos:
            formato = datos[0].formato
            year = datos[0].year
        else:
            raise UserError("No hay datos para generar el archivo")
        headers = self._get_dynamic_headers(formato, year)
        for index, header in enumerate(headers, start=12):
            sheet.write(0, index, header, titulo)

        i=0
        for line in datos:
            i=i+1
            num =0
            num = self.comprueba_escribe(sheet,i,num,line.concepto,celda)
            num = self.comprueba_escribe(sheet,i,num,line.tipo_documento,celda)
            num = self.comprueba_escribe(sheet,i,num,line.numero_identificacion,celda)
            num = self.comprueba_escribe(sheet,i,num,line.primer_apellido,celda)
            num = self.comprueba_escribe(sheet,i,num,line.segundo_apellido,celda)
            num = self.comprueba_escribe(sheet,i,num,line.primer_nombre,celda)
            num = self.comprueba_escribe(sheet,i,num,line.segundo_nombre,celda)
            num = self.comprueba_escribe(sheet,i,num,line.razon_social,celda)
            num = self.comprueba_escribe(sheet,i,num,line.direccion,celda)
            num = self.comprueba_escribe(sheet,i,num,line.codigo_dpto,celda)

            num = self.comprueba_escribe(sheet,i,num,line.codigo_mcp,celda)
            num = self.comprueba_escribe(sheet,i,num,line.codigo_pais,celda)
            for field_number in range(1, 17):
                field_name = 'field_%s' % field_number
                if field_number <= len(headers):
                    num = self.comprueba_escribe(
                        sheet,
                        i,
                        num,
                        "{:.2f}".format(self._safe_float(getattr(line, field_name))),
                        celda,
                    )
        
    def comprueba_escribe(self, sheet,i,num,concepto,celda):
        if concepto == False:
            pass
        else:
            sheet.write(i,num, concepto,celda) 
        num =num+1
        return num
        # print("revizando el concepto")
        # print(concepto)
        # print("y comprobando")
        # print(concepto != "False")
        # print()

class medios_magneticos(models.TransientModel):
    _name = 'account.medios_magneticos'
    _description = 'Medios Magnéticos'

    name = fields.Char(string='Nombre')
    tipo_documento = fields.Char()
    numero_identificacion = fields.Char()
    dv = fields.Char()
    concepto = fields.Char()
    primer_apellido = fields.Char()
    segundo_apellido = fields.Char()
    primer_nombre = fields.Char()
    segundo_nombre = fields.Char()
    razon_social = fields.Char()
    direccion = fields.Char()
    codigo_dpto = fields.Char("Código dpto")
    nombre_dpto = fields.Char("Nombre dpto")
    codigo_mcp = fields.Char("Código mcp")
    nombre_mcp = fields.Char("Nombre mcp")
    pais = fields.Char()
    codigo_pais = fields.Char("Código país")
    
    account_id = fields.Many2one('account.account',string='Cuenta')
    saldo = fields.Char()
    field_1 = fields.Char(string='field 1')
    field_2 = fields.Char(string='field 2')
    field_3 = fields.Char(string='field 3')
    field_4 = fields.Char(string='field 4')
    field_5 = fields.Char(string='field 5')
    field_6 = fields.Char(string='field 6')
    field_7 = fields.Char(string='field 7')
    field_8 = fields.Char(string='field 8')
    field_9 = fields.Char(string='field 9')
    field_10 = fields.Char(string='field 10')
    field_11 = fields.Char(string='field 11')
    field_12 = fields.Char(string='field 12')
    field_13 = fields.Char(string='field 13')
    field_14 = fields.Char(string='field 14')
    field_15 = fields.Char(string='field 15')
    field_16 = fields.Char(string='field 16')
    field_17 = fields.Char(string='field 17')
    
    tipo_documento2 = fields.Char()
    numero_identificacion2 = fields.Char()
    dv2 = fields.Char()
    primer_apellido2 = fields.Char()
    segundo_apellido2 = fields.Char()
    primer_nombre2 = fields.Char()
    segundo_nombre2 = fields.Char()
    razon_social2 = fields.Char()
    direccion2 = fields.Char()
    codigo_dpto2 = fields.Char("Código dpto2")
    nombre_dpto2 = fields.Char("Nombre dpto2")
    codigo_mcp2 = fields.Char("Código mcp2")
    nombre_mcp2 = fields.Char("Nombre mcp2")
    pais2 = fields.Char()
    codigo_pais2 = fields.Char("Código país 2")
    year = fields.Char("year")
    formato = fields.Char("formato")



    # value = fields.Integer()
    # value2 = fields.Float(compute="_value_pc", store=True)
    # description = fields.Text()

    # @api.depends('value')
    # def _value_pc(self):
    #     self.value2 = float(self.value) / 100
    
    # def __init__(self, cr, uid, context=None):
    #     print(context)
    #     super(medios_magneticos, self).__init__(cr, uid, context=context)
    #     self.open_taxes()
    #     self.localcontext.update({
    #         'next_seq': self._get_next_seq,
    #         'select_value': self._selection_value,
    #     })
    # @api.model
    # def default_get(self, fields):
    #     print("FIELDS", fields)
    #     self.open_taxes()
    #     rec = super(medios_magneticos, self).default_get(fields)
    #     print("REC", rec)
    #     context = dict(self._context or {})
    #     # partner = self.env['res.partner'].browse(context['partner_id'])
    #     # rec['partner_m2m'] = [(6, 0, partner.child_ids.ids)] # if your field type is many2many
    #     # rec['partner_m2m'] = [(0, 0, {'fieldname': value})] # if your field type is one2many
    #     return rec


    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', context=None, toolbar=False,submenu=False): 
        result = super(medios_magneticos,self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if view_type == 'tree':
            labels = self._get_dynamic_field_labels()
            for index, label in enumerate(labels[:16], start=1):
                for node in doc.xpath("//field[@name='field_%s']" % index):
                    node.set('string', label)
            result['arch'] = etree.tostring(doc)
        return result
    
    def get_context_values(self):
        context = self.env.context
        #print(fields.Date.context_today(self))
        return (
            context.get('from_date', fields.Date.context_today(self)),
            context.get('to_date', fields.Date.context_today(self)),
            context.get('company_id', self.env.user.company_id.id),
            context.get('formato', '1008'),
        )

    # @api.multi
    def open_taxes(self):
        #print('consiguiendo')
        from_date, to_date, company_id, formato = self.get_context_values()
        #print('despues de conseguir')
        #print(from_date)
        domain = self.get_move_line_partial_domain(
            from_date, to_date, company_id)
        conceptos = self.env['account.concepto'].search(
            [
                ('formato', '=', formato)
            ])
        #print('ano')
        # print(from_date.year)
        # count = self.env['account.asoconcepto'].search(
        #     [
        #         ('year', '=', ),
        #         ('company_id', '=', self.company_id.id)
        #     ])
        return #vals

    def get_move_line_partial_domain(self, from_date, to_date, company_id):
        return [
            ('date', '<=', to_date),
            ('date', '>=', from_date),
            # ('company_id', '=', company_id),
        ]
    def _get_dynamic_field_labels(self, formato=None, year=None):
        formato = formato or self.env.context.get('formato')
        year = year or self.env.context.get('year')

        if not formato or not year:
            sample_record = self.search([], limit=1, order='id desc')
            formato = formato or sample_record.formato
            year = year or sample_record.year

        labels = []
        seen = set()
        if formato and year:
            association_records = self.env['account.asoconcepto'].search([
                ('formaton', '=', formato),
                ('year', '=', str(year)),
            ])
            for category_name in association_records.mapped('categoria.name'):
                if category_name and category_name not in seen:
                    seen.add(category_name)
                    labels.append(category_name)

        if labels:
            return labels

        if formato and year:
            config_records = self.env['account.exogena_config'].search([
                ('formato', '=', formato),
                ('year', '=', str(year)),
            ])
            for category_name in config_records.mapped('categoria_nombre'):
                if category_name and category_name not in seen:
                    seen.add(category_name)
                    labels.append(category_name)

        if labels:
            return labels

        categoria_records = self.env['account.categoria'].search([
            ('formato', '=', formato),
            ('year', '=', str(year)),
        ]) if formato and year else self.env['account.categoria']

        for categoria in categoria_records:
            if categoria.name and categoria.name not in seen:
                seen.add(categoria.name)
                labels.append(categoria.name)
        return labels
