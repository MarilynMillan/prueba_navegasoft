# Instructivo: Eventos RADIAN en Odoo 18
## Módulo `l10n_co_dian_extended`

---

## 1. ¿Qué es RADIAN?

**RADIAN** (Registro de Facturas Electrónicas de Venta como Título Valor) es el sistema de la DIAN que permite hacer seguimiento del ciclo comercial de una factura electrónica. A través de RADIAN, tanto el **vendedor (emisor)** como el **comprador (adquirente)** notifican a la DIAN cada paso del proceso: si recibieron la factura, si recibieron los bienes, si aceptan o rechazan la factura, etc.

Cada paso se notifica enviando un **ApplicationResponse** (XML firmado) al webservice `SendEventUpdateStatus` de la DIAN.

---

## 2. Estados del Ciclo Comercial

El ciclo RADIAN define **5 eventos posibles** que avanzan el estado comercial de la factura:

```
PENDIENTE
    │
    ▼ Evento 030
ACUSE DE RECIBO (030)
    │
    ▼ Evento 032
RECIBO DEL BIEN (032)
    │
    ├──▼ Evento 033──► ACEPTACIÓN EXPRESA (033)
    │
    └──▼ Evento 031──► RECLAMO (031)  [fin del flujo para el adquirente]

Paralelamente (lado vendedor):
    │
    ▼ Evento 034
ACEPTACIÓN TÁCITA (034)  [emitido por el vendedor después de 3 días hábiles]
```

| Código | Nombre | Quién lo envía | Estado en Odoo |
|--------|--------|---------------|----------------|
| 030 | Acuse de recibo | Adquirente (comprador) | `received` |
| 031 | Reclamo | Adquirente (comprador) | `claimed` |
| 032 | Recibo del bien y/o servicio | Adquirente (comprador) | `goods_received` |
| 033 | Aceptación expresa | Adquirente (comprador) | `accepted` |
| 034 | Aceptación tácita | Emisor (vendedor) | `accepted_by_issuer` |

---

## 3. ¿Dónde se ven y gestionan los eventos en Odoo?

### 3.1 En facturas de compra (Facturas Proveedor — lado adquirente)

El adquirente gestiona los eventos 030, 031, 032 y 033.

**Ruta:** `Contabilidad > Proveedores > Facturas`

Al abrir una factura de proveedor confirmada (estado `Publicada`), aparecen los botones de eventos en la barra superior:

```
[ Acusar Recibo (030) ]   [ Recibir Bienes (032) ]   [ Aceptar (033) ]   [ Reclamar (031) ]
```

Estos botones aparecen y desaparecen según el estado comercial actual:

| Estado actual | Botón visible |
|--------------|--------------|
| Pendiente | **Acusar Recibo (030)** |
| Acuse de Recibo | **Recibir Bienes (032)** |
| Recibo del Bien | **Aceptar (033)** y **Reclamar (031)** |

### 3.2 En facturas de venta (lado emisor)

El emisor solo gestiona el evento 034 (Aceptación Tácita).

**Ruta:** `Contabilidad > Clientes > Facturas`

Aparece el botón **Aceptación Tácita (034)** cuando la factura de venta se encuentra en estado comercial `Recibo del Bien` y han pasado 3 días hábiles sin respuesta del adquirente.

### 3.3 Estado Comercial visible en las listas

En las listas de facturas de venta y compra aparece la columna **Estado Comercial** (opcional, activable con el ícono de columnas).

---

## 4. Flujo completo paso a paso (lado adquirente — Facturas Proveedor)

### Paso 0: Prerrequisitos

Antes de poder enviar eventos RADIAN, la factura de proveedor debe tener:

- **Estado:** Publicada (confirmada)
- **Referencia de factura (campo Ref.):** número de la factura del proveedor, p. ej. `FV-2024-001`
- **CUFE/CUDE:** el código único de la factura electrónica del proveedor

> **Cómo llega el CUFE:** Si la factura se importó desde un archivo XML electrónico del proveedor, el CUFE se carga automáticamente. Si se creó manualmente, debe ingresarse en el campo **CUFE/CUDE** que aparece en el encabezado de la factura.

---

### Paso 1: Acuse de Recibo (Evento 030)

**¿Qué hace?** Notifica a la DIAN que el adquirente recibió la factura electrónica.

**En Odoo:**
1. Abrir la factura de proveedor publicada
2. El estado comercial muestra **Pendiente**
3. Hacer clic en **Acusar Recibo (030)**
4. Odoo genera el XML `ApplicationResponse` firmado y lo envía a la DIAN
5. Si la DIAN acepta, el estado cambia a **030 - Received**
6. Se genera automáticamente el **AttachedDocument** (ZIP con la factura original + el evento)
7. Se envía un correo al proveedor notificando el evento

---

### Paso 2: Recibo del Bien (Evento 032)

**¿Qué hace?** Confirma que los bienes o servicios fueron recibidos físicamente.

**En Odoo:**
1. Con la factura en estado **030 - Received**
2. Hacer clic en **Recibir Bienes (032)**
3. Odoo genera y envía el `ApplicationResponse` del evento 032
4. El estado cambia a **032 - Goods Received**
5. Se actualiza el AttachedDocument con el historial acumulado (factura + evento 030 + evento 032)

---

### Paso 3a: Aceptación Expresa (Evento 033)

**¿Qué hace?** El adquirente acepta expresamente la factura. La factura queda como título valor negociable.

**En Odoo:**
1. Con la factura en estado **032 - Goods Received**
2. Hacer clic en **Aceptar (033)**
3. Odoo genera y envía el `ApplicationResponse` del evento 033
4. El estado cambia a **033 - Accepted by Customer**

---

### Paso 3b: Reclamo (Evento 031) — alternativa a Aceptar

**¿Qué hace?** El adquirente rechaza la factura indicando el motivo.

**En Odoo:**
1. Con la factura en estado **032 - Goods Received**
2. Hacer clic en **Reclamar (031)**
3. Se abre un **wizard** (ventana emergente) para seleccionar el motivo del reclamo:

   | Código | Motivo |
   |--------|--------|
   | 01 | Documentos con inconsistencias |
   | 02 | Mercancía no entregada |
   | 03 | Mercancía parcialmente entregada |
   | 04 | Servicio no prestado |

4. Seleccionar el motivo y hacer clic en **Reclamar**
5. El estado cambia a **031 - Claimed**

---

### Paso 4 (lado vendedor): Aceptación Tácita (Evento 034)

**¿Qué hace?** Si el adquirente no respondió en **3 días hábiles** desde el Recibo del Bien, el emisor puede notificar la aceptación tácita.

**En Odoo (desde la factura de venta):**
1. Abrir la factura de venta correspondiente
2. Con estado comercial **032 - Goods Received**
3. Hacer clic en **Aceptación Tácita (034)**
4. El estado cambia a **034 - Accepted by Issuer**

---

## 5. Campo CUFE/CUDE en Facturas de Proveedor

Para poder enviar eventos RADIAN en facturas ingresadas **manualmente** (no importadas desde XML), es obligatorio completar el campo **CUFE/CUDE**:

- Se encuentra en el encabezado de la factura de proveedor, sección izquierda
- Solo visible cuando la empresa tiene habilitado el módulo DIAN (`l10n_co_dian_is_enabled`)
- El campo es editable en facturas de compra

---

## 6. Tab DIAN — Historial de Documentos

En cualquier factura (venta o compra), la pestaña **DIAN** muestra el historial de documentos enviados:

| Columna | Descripción |
|---------|------------|
| Fecha | Fecha y hora del envío |
| Estado | `Aceptado`, `Rechazado`, `Pendiente`, `Fallo de envío` |
| Estado Comercial | Estado RADIAN del documento |
| CUFE/CUDE | Identificador único |
| Botón **Download** | Descarga el archivo ZIP enviado a la DIAN |
| Botón **Fetch Attached Document** | Recupera el AttachedDocument completo con historial |
| Botón **Get Status** | Consulta el estado en entorno de certificación |

---

## 7. Actualización Automática de Estados (CRON)

El módulo incluye un **CRON diario** (se ejecuta a las 6:00 PM) que consulta automáticamente la DIAN para actualizar el estado comercial de las facturas de venta que estén en estados intermedios (`Pendiente`, `030 - Received`, `032 - Goods Received`).

- Procesa máximo **3 facturas por ejecución** para evitar sobrecargar el servidor
- Solo procesa facturas con menos de **30 días** desde su fecha de emisión
- Configurable en: `Ajustes Técnicos > Automatización > Acciones Planificadas > Colombian EDI: Update Invoice Commercial States`

---

## 8. Botón "Actualizar Estado Comercial" (manual)

En facturas de venta con estado DIAN aceptado, aparece un ícono de **actualizar** (↻) junto al Estado Comercial:

- Consulta la DIAN en tiempo real el estado actual de los eventos
- Útil cuando se quiere verificar si el proveedor ya envió algún evento

---

## 9. Notificación por Correo

Cada vez que se envía un evento RADIAN exitosamente, Odoo envía automáticamente un correo al **partner** de la factura con:

- **Asunto:** `Evento;{número_factura};{NIT_empresa};{nombre_empresa};{num_documento};{código_evento}`
- **Adjunto:** El archivo ZIP del AttachedDocument (factura + eventos)
- **Plantilla:** `Colombia Commercial Event`

---

## 10. AttachedDocument: ¿Qué es?

El **AttachedDocument** es el contenedor XML que empaqueta:

1. La factura electrónica original (en formato UBL 2.1)
2. Cada `ApplicationResponse` de los eventos enviados (en orden cronológico)

Este archivo es el que se envía a la DIAN como evidencia del estado del título valor. Se genera y actualiza automáticamente en cada evento exitoso.

**Formato del nombre del archivo:** `z{NIT_empresa}000{año}{secuencia_hex}.zip`

Ejemplo: `z8001234560002501000001A.zip`

---

## 11. Proceso de Certificación DIAN

Antes de operar en producción, la DIAN exige un proceso de certificación. El módulo incluye herramientas para esto:

**Ruta:** `Contabilidad > Configuración > Ajustes > sección DIAN`

Con el **Proceso de Certificación** activado:
- Aparecen contadores configurables: número de facturas, notas crédito y notas débito de prueba (0-10 cada uno, por defecto 5)
- El botón **Iniciar Proceso de Certificación** crea automáticamente los diarios, productos y movimientos de prueba requeridos por la DIAN

> **Advertencia:** Este proceso modifica la base de datos de forma irreversible. Ejecutarlo solo en una base de datos de pruebas dedicada a certificación.

---

## 12. Requisitos Técnicos

Para que el módulo funcione correctamente se necesita:

| Requisito | Descripción |
|-----------|-------------|
| Módulo base | `l10n_co_dian` (Enterprise) instalado |
| Certificado digital | Archivo `.p12` o `.pfx` de firma electrónica |
| Software DIAN | ID y código de seguridad del software registrado en la DIAN |
| Modo de operación | Configurado en `Ajustes > DIAN > Modos de Operación` (factura y/o documento soporte) |
| NIT empresa | Registrado correctamente con dígito verificador |
| Entorno | Habilitación (pruebas) o Producción configurado |

---

## 13. Errores Comunes y Soluciones

| Error | Causa probable | Solución |
|-------|---------------|---------|
| "El CUFE/CUDE es requerido" | Factura sin CUFE | Ingresar manualmente el CUFE en el campo correspondiente |
| "El NIT del partner es requerido" | Partner sin NIT | Completar el campo NIT en la ficha del proveedor |
| "The Bill Reference is required" | Campo Ref. vacío | Ingresar el número de la factura del proveedor |
| DIAN retorna estado `Rechazado` | XML inválido o datos incorrectos | Revisar el mensaje de error en la tab DIAN |
| "Regla: 90, Rechazo: Documento procesado" | Factura ya fue enviada previamente | El sistema valida automáticamente y recupera el CUFE si los datos coinciden |
| Botones de evento no aparecen | Estado no es `Publicada` o no hay DIAN habilitado | Verificar que la factura esté publicada y la empresa tenga DIAN configurado |

---

## 14. Flujo Resumido en Diagrama

```
FACTURA PROVEEDOR (in_invoice)
          │
          │ Confirmación (_post)
          ▼
   [Documento DIAN creado]
   estado_comercial = PENDIENTE
          │
          │ Clic "Acusar Recibo (030)"
          ▼
   ApplicationResponse 030
   enviado a DIAN ──────────► DIAN valida y responde
          │                          │
          │ Aceptado                 │ Rechazado
          ▼                         ▼
   estado_comercial = RECEIVED    [Error en tab DIAN]
   AttachedDocument generado
          │
          │ Clic "Recibir Bienes (032)"
          ▼
   ApplicationResponse 032
   enviado a DIAN ──────────► DIAN valida y responde
          │
          ▼
   estado_comercial = GOODS_RECEIVED
   AttachedDocument actualizado (factura + 030 + 032)
          │
          ├─── Clic "Aceptar (033)" ──► estado = ACCEPTED
          │                             Factura: título valor negociable
          │
          └─── Clic "Reclamar (031)" ──► Seleccionar motivo
                                         estado = CLAIMED

FACTURA DE VENTA (out_invoice) — después de 3 días sin respuesta:
          │
          └─── Clic "Aceptación Tácita (034)" ──► estado = ACCEPTED_BY_ISSUER
```

---

*Documento generado para el módulo `l10n_co_dian_extended` v18.0.2.0.0 — MI ERP*
