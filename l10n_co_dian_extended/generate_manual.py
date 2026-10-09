#!/usr/bin/env python3
"""Genera manual PDF del modulo l10n_co_dian_extended."""
import base64, os, subprocess, tempfile

SDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots')

def img(f):
    path = os.path.join(SDIR, f)
    if not os.path.exists(path): return ''
    with open(path, 'rb') as fh:
        return f'data:image/png;base64,{base64.b64encode(fh.read()).decode()}'

HTML = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<style>
@page {{ size: A4; margin: 20mm 18mm; }}
body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #333; }}
h1 {{ color: #714B67; font-size: 22pt; border-bottom: 3px solid #714B67; padding-bottom: 8px; margin-top: 0; }}
h2 {{ color: #714B67; font-size: 16pt; border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 30px; page-break-after: avoid; }}
h3 {{ color: #555; font-size: 13pt; margin-top: 22px; page-break-after: avoid; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }}
th {{ background-color: #714B67; color: white; padding: 8px 10px; text-align: left; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #e0e0e0; }}
tr:nth-child(even) td {{ background-color: #f8f6f7; }}
.ss {{ text-align: center; margin: 16px 0; page-break-inside: avoid; }}
.ss img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
.ss .cap {{ font-size: 9pt; color: #888; margin-top: 4px; font-style: italic; }}
.note {{ background: #fef8e7; border-left: 4px solid #f0ad4e; padding: 10px 14px; margin: 12px 0; font-size: 10pt; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 9pt; color: white; }}
.badge-warning {{ background: #e9a820; }}
.badge-info {{ background: #17a2b8; }}
.badge-success {{ background: #28a745; }}
.badge-danger {{ background: #dc3545; }}
.cover {{ text-align: center; padding-top: 100px; page-break-after: always; }}
.cover h1 {{ font-size: 28pt; border: none; }}
.cover .sub {{ font-size: 16pt; color: #666; margin-bottom: 40px; }}
.cover .co {{ font-size: 14pt; color: #714B67; font-weight: bold; margin-top: 60px; }}
.cover .ver {{ font-size: 11pt; color: #999; margin-top: 10px; }}
.toc {{ page-break-after: always; }}
.toc ul {{ list-style: none; padding: 0; }}
.toc li {{ padding: 4px 0; border-bottom: 1px dotted #ccc; }}
.toc ul ul {{ padding-left: 20px; }}
.toc ul ul li {{ border-bottom: none; font-size: 10pt; }}
.pb {{ page-break-before: always; }}
code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }}
ol {{ margin-left: 15px; }}
</style></head><body>

<!-- PORTADA -->
<div class="cover">
<h1>Manual de Usuario</h1>
<div class="sub">Colombia: Eventos RADIAN y Documento Soporte</div>
<p style="font-size:12pt; color:#888">Modulo: l10n_co_dian_extended</p>
<div class="co">GRUPO MI ERP SAS</div>
<div class="ver">Version 18.0.2.0.0<br>Odoo 18 Enterprise</div>
</div>

<!-- TOC -->
<div class="toc">
<h2>Tabla de Contenido</h2>
<ul>
<li><strong>1. Introduccion</strong></li>
<li><strong>2. Requisitos</strong></li>
<li><strong>3. Flujo de Eventos RADIAN</strong>
<ul><li>3.1 Acuse de Recibo (030)</li><li>3.2 Recepcion de Bienes (032)</li>
<li>3.3 Aceptacion Expresa (033)</li><li>3.4 Reclamacion (031)</li>
<li>3.5 Aceptacion del Emisor (034)</li></ul></li>
<li><strong>4. Facturas de Compra</strong>
<ul><li>4.1 Vista de Lista</li><li>4.2 Formulario con Botones RADIAN</li></ul></li>
<li><strong>5. Facturas de Venta</strong></li>
<li><strong>6. Wizard de Reclamacion</strong></li>
<li><strong>7. Configuracion</strong></li>
<li><strong>8. Procesos Automaticos</strong></li>
</ul>
</div>

<!-- 1. INTRODUCCION -->
<h2>1. Introduccion</h2>
<p>El modulo <strong>l10n_co_dian_extended</strong> extiende la facturacion electronica de Odoo 18 para Colombia,
agregando soporte completo para los <strong>Eventos RADIAN</strong> de la DIAN (Resolucion 000085 de 2022).</p>

<p>Los eventos RADIAN permiten gestionar el ciclo de vida comercial de las facturas electronicas:</p>

<table>
<tr><th>Codigo</th><th>Evento</th><th>Descripcion</th></tr>
<tr><td><strong>030</strong></td><td>Acuse de Recibo</td><td>Confirma que la factura fue recibida</td></tr>
<tr><td><strong>031</strong></td><td>Reclamacion</td><td>Rechaza la factura por inconsistencias</td></tr>
<tr><td><strong>032</strong></td><td>Recepcion de Bienes</td><td>Confirma recepcion de bienes/servicios</td></tr>
<tr><td><strong>033</strong></td><td>Aceptacion Expresa</td><td>Acepta formalmente la factura</td></tr>
<tr><td><strong>034</strong></td><td>Aceptacion del Emisor</td><td>El emisor acepta la factura (lado vendedor)</td></tr>
</table>

<h3>Funcionalidades adicionales</h3>
<ul>
<li><strong>AttachedDocument con historial:</strong> Genera documentos XML con todos los eventos registrados</li>
<li><strong>Validacion de duplicados:</strong> Consulta GetXmlByDocumentKey antes de registrar facturas</li>
<li><strong>CRON automatico:</strong> Actualiza estados comerciales diariamente</li>
<li><strong>Campo CUFE editable:</strong> Permite ingresar el CUFE manualmente en facturas de compra</li>
</ul>

<!-- 2. REQUISITOS -->
<h2>2. Requisitos</h2>
<ul>
<li><strong>Odoo 18 Enterprise</strong> con modulo <code>l10n_co_dian</code> instalado</li>
<li>Certificado digital vigente para comunicacion con la DIAN</li>
<li>Resolucion de facturacion activa</li>
<li>Set de pruebas de la DIAN (para ambiente de habilitacion)</li>
</ul>

<!-- 3. FLUJO RADIAN -->
<h2 class="pb">3. Flujo de Eventos RADIAN</h2>

<p>El flujo RADIAN sigue un orden especifico para facturas de compra (lado receptor):</p>

<table>
<tr><th>Estado</th><th>Badge</th><th>Siguiente Accion</th></tr>
<tr><td>Pendiente</td><td><span class="badge badge-warning">Pendiente</span></td><td>Enviar Acuse de Recibo (030)</td></tr>
<tr><td>030 - Acuse de Recibo</td><td><span class="badge badge-info">030 - Acuse de Recibo</span></td><td>Enviar Recepcion de Bienes (032)</td></tr>
<tr><td>032 - Bienes Recibidos</td><td><span class="badge badge-info">032 - Bienes Recibidos</span></td><td>Aceptar (033) o Reclamar (031)</td></tr>
<tr><td>033 - Aceptada</td><td><span class="badge badge-success">033 - Aceptada</span></td><td>Proceso completado</td></tr>
<tr><td>031 - Reclamada</td><td><span class="badge badge-danger">031 - Reclamada</span></td><td>Factura rechazada</td></tr>
</table>

<h3>3.1 Acuse de Recibo (030)</h3>
<p>Primer evento del flujo. Confirma ante la DIAN que la factura electronica fue recibida por el comprador.</p>
<ol>
<li>Abra la factura de compra en estado <strong>Publicado</strong></li>
<li>Haga clic en el boton <strong>"Acusar Recibo (030)"</strong></li>
<li>El sistema envia el evento a la DIAN y actualiza el estado a <strong>030 - Acuse de Recibo</strong></li>
</ol>

<div class="ss">
<img src="{img('04_factura_pendiente.png')}">
<div class="cap">Figura 1: Factura pendiente con boton "Acusar Recibo (030)"</div>
</div>

<h3>3.2 Recepcion de Bienes (032)</h3>
<p>Segundo evento. Confirma que los bienes o servicios fueron recibidos satisfactoriamente.</p>
<ol>
<li>Desde una factura con estado <strong>030 - Acuse de Recibo</strong></li>
<li>Haga clic en <strong>"Recibir Bienes (032)"</strong></li>
<li>El estado cambia a <strong>032 - Bienes Recibidos</strong></li>
</ol>

<div class="ss">
<img src="{img('06_estado_recibido_030.png')}">
<div class="cap">Figura 2: Factura con estado "030 - Acuse de Recibo" y boton para evento 032</div>
</div>

<h3>3.3 Aceptacion Expresa (033)</h3>
<p>Evento final positivo. Acepta formalmente la factura ante la DIAN.</p>
<ol>
<li>Desde una factura con estado <strong>032 - Bienes Recibidos</strong></li>
<li>Haga clic en <strong>"Aceptar (033)"</strong></li>
<li>El estado cambia a <strong>033 - Aceptada</strong> (verde)</li>
</ol>

<div class="ss">
<img src="{img('07_bienes_recibidos_032.png')}">
<div class="cap">Figura 3: Factura con bienes recibidos - botones Aceptar (033) y Reclamar (031)</div>
</div>

<h3>3.4 Reclamacion (031)</h3>
<p>Evento de rechazo. Permite rechazar una factura indicando el motivo.</p>
<ol>
<li>Desde una factura con estado <strong>032 - Bienes Recibidos</strong></li>
<li>Haga clic en <strong>"Reclamar (031)"</strong></li>
<li>Se abre un wizard donde debe seleccionar el <strong>motivo de rechazo</strong></li>
<li>Haga clic en <strong>"Reclamar"</strong> para confirmar</li>
</ol>

<p>Motivos de rechazo disponibles:</p>
<table>
<tr><th>Codigo</th><th>Motivo</th></tr>
<tr><td>01</td><td>Documentos con inconsistencias</td></tr>
<tr><td>02</td><td>Mercancia no entregada</td></tr>
<tr><td>03</td><td>Mercancia parcialmente entregada</td></tr>
<tr><td>04</td><td>Servicio no prestado</td></tr>
</table>

<div class="ss">
<img src="{img('08_wizard_reclamar_031.png')}">
<div class="cap">Figura 4: Wizard de reclamacion - Evento RADIAN 031</div>
</div>

<h3>3.5 Aceptacion del Emisor (034)</h3>
<p>Para facturas de <strong>venta</strong>, el emisor puede aceptar la factura una vez el comprador la ha aceptado.
Este evento se procesa automaticamente o mediante el CRON diario.</p>

<!-- 4. FACTURAS COMPRA -->
<h2 class="pb">4. Facturas de Compra</h2>

<h3>4.1 Vista de Lista</h3>
<p>La lista de facturas de compra muestra la columna <strong>"Estado Comercial"</strong> con badges de colores
que permiten identificar rapidamente el estado RADIAN de cada factura:</p>

<div class="ss">
<img src="{img('03_facturas_compra_lista.png')}">
<div class="cap">Figura 5: Lista de facturas de compra con columna Estado Comercial</div>
</div>

<h3>4.2 Formulario con Botones RADIAN</h3>
<p>En el formulario de cada factura aparecen los botones de eventos RADIAN segun el estado actual:</p>

<table>
<tr><th>Estado Actual</th><th>Botones Visibles</th></tr>
<tr><td>Pendiente (sin eventos)</td><td><strong>Acusar Recibo (030)</strong></td></tr>
<tr><td>030 - Acuse de Recibo</td><td><strong>Recibir Bienes (032)</strong></td></tr>
<tr><td>032 - Bienes Recibidos</td><td><strong>Aceptar (033)</strong> + <strong>Reclamar (031)</strong></td></tr>
<tr><td>033 - Aceptada / 031 - Reclamada</td><td>Ninguno (flujo completado)</td></tr>
</table>

<div class="ss">
<img src="{img('05_botones_radian_header.png')}">
<div class="cap">Figura 6: Header con botones RADIAN y campo Estado Comercial</div>
</div>

<div class="note">
<strong>Campo CUFE:</strong> Para facturas de compra ingresadas manualmente (sin importacion XML),
el campo CUFE/CUDE es editable y debe ingresarse manualmente para poder enviar eventos RADIAN.
</div>

<!-- 5. FACTURAS VENTA -->
<h2 class="pb">5. Facturas de Venta</h2>
<p>Las facturas de venta tambien muestran el estado comercial, pero del lado del <strong>emisor</strong>.
El estado se actualiza automaticamente cuando el comprador envia eventos:</p>

<div class="ss">
<img src="{img('09_factura_venta.png')}">
<div class="cap">Figura 7: Factura de venta con campo Estado Comercial</div>
</div>

<p>Lista de facturas de venta con la columna de estado comercial:</p>
<div class="ss">
<img src="{img('10_facturas_venta_lista.png')}">
<div class="cap">Figura 8: Lista de facturas de venta</div>
</div>

<!-- 6. WIZARD -->
<h2>6. Wizard de Reclamacion</h2>
<p>El wizard se activa al hacer clic en <strong>"Reclamar (031)"</strong> y permite:</p>
<ul>
<li>Seleccionar el motivo de rechazo de una lista predefinida por la DIAN</li>
<li>Confirmar el envio del evento de reclamacion</li>
<li>Cancelar si se desea volver sin enviar</li>
</ul>
<p>Una vez enviado, la factura queda en estado <strong>031 - Reclamada</strong> (badge rojo) y no puede
avanzar en el flujo RADIAN.</p>

<!-- 7. CONFIGURACION -->
<h2 class="pb">7. Configuracion</h2>

<h3>7.1 Proceso de Certificacion DIAN</h3>
<p>El modulo agrega contadores para el proceso de certificacion ante la DIAN:</p>
<ul>
<li><strong>Facturas de prueba:</strong> Contador de 0 a 10 facturas enviadas</li>
<li><strong>Notas credito de prueba:</strong> Contador de 0 a 10</li>
<li><strong>Notas debito de prueba:</strong> Contador de 0 a 10</li>
</ul>
<p>Acceda desde <strong>Configuracion &rarr; Contabilidad &rarr; Facturacion Electronica</strong>.</p>

<div class="ss">
<img src="{img('11_configuracion.png')}">
<div class="cap">Figura 9: Pantalla de configuracion</div>
</div>

<!-- 8. PROCESOS AUTOMATICOS -->
<h2>8. Procesos Automaticos</h2>

<h3>8.1 CRON de Actualizacion de Estados</h3>
<p>El sistema ejecuta automaticamente un proceso diario (18:00) que:</p>
<ul>
<li>Consulta el estado de las facturas de venta en estados intermedios</li>
<li>Actualiza el estado comercial segun la respuesta de la DIAN</li>
<li>Procesa maximo 3 facturas por ejecucion</li>
<li>Solo procesa facturas emitidas en los ultimos 30 dias</li>
</ul>

<h3>8.2 Notificaciones por Correo</h3>
<p>Despues de cada evento RADIAN exitoso, se envia una notificacion por correo electronico que incluye:</p>
<ul>
<li>Codigo del evento enviado</li>
<li>Numero de factura</li>
<li>NIT de la empresa</li>
<li>Archivo ZIP adjunto con el AttachedDocument (XML de factura + eventos)</li>
</ul>

<h3>8.3 Servicios DIAN Utilizados</h3>
<table>
<tr><th>Servicio</th><th>Descripcion</th></tr>
<tr><td><code>SendEventUpdateStatus</code></td><td>Envia eventos RADIAN (030, 031, 032, 033, 034)</td></tr>
<tr><td><code>GetStatusEvent</code></td><td>Consulta el estado actual de eventos de una factura</td></tr>
<tr><td><code>GetXmlByDocumentKey</code></td><td>Recupera XML original de la DIAN por CUFE (validacion de duplicados)</td></tr>
</table>

<hr>
<p style="text-align:center; font-size:9pt; color:#999; margin-top:40px">
Manual del modulo l10n_co_dian_extended v18.0.2.0.0<br>
GRUPO MI ERP SAS &bull; www.mi-erp.app
</p>
</body></html>"""


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'Manual_Eventos_RADIAN.pdf')
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(HTML)
        html = f.name

    try:
        subprocess.run([
            'wkhtmltopdf', '--encoding', 'UTF-8', '--page-size', 'A4',
            '--margin-top', '18mm', '--margin-bottom', '18mm',
            '--margin-left', '16mm', '--margin-right', '16mm',
            '--footer-center', 'Pagina [page] de [topage]',
            '--footer-font-size', '8', '--footer-spacing', '5',
            '--enable-local-file-access', '--print-media-type',
            '--no-stop-slow-scripts', '--javascript-delay', '500',
            html, out
        ], capture_output=True, text=True, timeout=120)

        if os.path.exists(out):
            mb = os.path.getsize(out) / (1024*1024)
            print(f"PDF generado: {out} ({mb:.1f} MB)")
        else:
            print("Error generando PDF")
    finally:
        os.unlink(html)


if __name__ == '__main__':
    main()
