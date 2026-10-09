# Colombia - Impuestos (actualización funcional)

## visión general

Este documento describe únicamente los cambios nuevos agregados al módulo para el cálculo de retenciones por umbral mínimo.

| campo | valor |
|---|---|
| módulo | `l10n_co_tax_extension-11` |
| versión base | Odoo 18 |
| alcance | ventas, compras y facturas |

## propósito principal

Agregar un modo global opcional para evaluar el umbral de retención con base en la suma de líneas aplicables del documento, manteniendo el comportamiento actual por línea cuando el modo global está desactivado.

## funcionalidades nuevas

1. Configuración global en contabilidad:
   - Ajustes > Contabilidad > Retención Colombia.
   - Campo: `Usar base global aplicable para retención`.
2. Producto aplicable:
   - Campo en producto (tab Contabilidad): `Aplica al umbral de retención`.
   - Si está desactivado, la línea no participa en la base global ni recibe retención.
3. Regla para líneas negativas:
   - Las líneas con base negativa ajustan (reducen) la base global.
   - Las líneas con base menor o igual a cero no disparan retención en su propia línea.
4. Recalculo automático al guardar:
   - Factura (`account.move`), venta (`sale.order`) y compra (`purchase.order`) recalculan al `write` cuando cambian líneas o posición fiscal.
5. Botón de factura:
   - `Calcular Impuestos` conserva recálculo forzado.
   - Se eliminó el comportamiento de alternancia (toggle) y doble clic.

## comportamiento funcional

### modo global desactivado

- Se conserva el cálculo por línea.
- Umbral evaluado con base de cada línea.

### modo global activado

- Se calcula una base global con la suma de líneas aplicables del documento.
- Si la base global supera el umbral, se agrega retención en líneas aplicables.
- Si no supera el umbral, no se agrega retención.

## validación funcional sugerida

1. Activar modo global y crear documento con 3 líneas aplicables.
2. Verificar que al editar una línea y guardar, las demás se recalculan.
3. Agregar línea no aplicable y verificar que no entra al umbral.
4. Agregar línea negativa y verificar que reduce la base global.
5. Ejecutar botón `Calcular Impuestos` en factura y verificar consistencia con el guardado.
