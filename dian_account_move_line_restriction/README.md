# DIAN - Restricción de líneas de factura

## Visión general

| Campo | Valor |
| --- | --- |
| Nombre técnico | `dian_account_move_line_restriction` |
| Nombre funcional | DIAN - Restricción de líneas de factura |
| Versión | `1.0.0` |
| Autor | Navegasoft |
| Sitio web | http://www.navegasoft.com |
| Licencia | OPL-1 |
| Tipo | Localización/Facturación electrónica DIAN |
| Aplicación | No (`auto_install = False`) |

## Propósito principal

Este módulo controla y agrupa líneas de factura de cliente para escenarios DIAN, limitando la cantidad de productos/variantes diferentes y asegurando consistencia entre:

- Visualización en PDF de factura.
- Exportación UBL DIAN (XML).
- Validación previa al envío e impresión.

## Idiomas soportados

| Idioma | Código |
| --- | --- |
| Español | `es` |
| Español (Colombia) | `es_CO` |
| Base (fuente de traducción) | `dian_account_move_line_restriction.pot` |

## Dependencias

- `account`
- `l10n_co_dian`

## Configuración requerida

1. Ir a **Contabilidad > Configuración > Ajustes**.
2. En bloque **DIAN grouped lines** configurar:
   - **Alcance para líneas agrupadas**.
   - **Diarios con agrupación** (si el alcance es por diario).
   - **Agrupar por producto** (`Por variante` o `Por plantilla`).
   - **Límite de líneas agrupadas para facturas**.
3. Verificar que los diarios de venta esperados estén seleccionados cuando se use alcance por diario.

## Guía de usuario

1. Crear/editar una factura de cliente.
2. Agregar líneas de producto.
3. El módulo calcula el total de líneas agrupadas por variante (`total_grouped_lines_by_variant`) cuando la agrupación DIAN aplica:
   - Siempre si el alcance es global.
   - Solo para los diarios configurados si el alcance es por diario.
   - El agrupamiento se hace por combinación de producto (variante o plantilla según configuración), impuestos, descuento y UoM.
4. Al imprimir o enviar, si se supera el límite configurado, se bloquea la acción con mensaje de validación.
5. En vista previa y PDF se muestran líneas agrupadas.
6. En XML UBL DIAN se exportan líneas agrupadas y se recalculan subtotales/impuestos.

## Detalles técnicos

### Modelos modificados

| Modelo | Tipo de cambio |
| --- | --- |
| `account.move` | Cálculo de total agrupado, alcance activo DIAN y validación de límite antes de imprimir/enviar. |
| `account.edi.xml.ubl_dian` | Agrupación de líneas para XML, merge de impuestos/descuentos y recálculo de totales. |
| `res.company` | Parámetros de alcance DIAN (`global`/`journal`) y diarios aplicables. |
| `res.config.settings` | Exposición de parámetros de compañía en Ajustes. |
| `report.account.report_invoice` | Reemplazo de líneas en reporte PDF con líneas agrupadas. |
| `report.account.report_invoice_with_payments` | Igual que el anterior para facturas con pagos. |

### Campos relevantes

| Modelo | Campo | Tipo |
| --- | --- | --- |
| `account.move` | `total_grouped_lines_by_variant` | Integer (compute, store) |
| `account.move` | `dian_grouping_active` | Boolean (compute) |
| `res.company` | `dian_grouping_scope` | Selection (`global`, `journal`) |
| `res.company` | `dian_grouping_journal_ids` | Many2many (`account.journal`) |
| `res.company` | `dian_grouping_product_mode` | Selection (`variant`, `template`) |
| `res.config.settings` | `grouped_lines_limit` | Integer (`ir.config_parameter`) |
| `res.config.settings` | `dian_grouping_product_mode` | Related Selection |

### Vistas y reportes

- `views/account_invoice_views.xml`
- `views/res_config_settings_views.xml`
- `views/report_invoice.xml`

### Seguridad

- Este módulo no agrega archivos de seguridad propios (`security/`), usa la seguridad estándar de los modelos heredados.

### Pruebas

- `tests/test_account_move_limit.py`
- `tests/test_account_edi_xml_ubl_dian.py`

## Notas operativas

- Aplica funcionalmente a facturas de cliente (`out_invoice`) para la lógica DIAN.
- Si el módulo DIAN/localización no está disponible, no debe instalarse por dependencia explícita de `l10n_co_dian`.
