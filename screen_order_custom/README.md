# Screen POS Custom v4.0

Módulo personalizado para la pantalla de preparación (Kitchen Display) de Odoo 18, desarrollado para Di'Silvio Trattoria.

## Descripción

Este módulo extiende la pantalla de preparación del POS para mejorar la visualización de comandas en cocina con tres funcionalidades principales:

### 1. Combos nativos de Odoo 18
Muestra los items del combo agrupados bajo el producto padre en la comanda de cocina. Utiliza el sistema de combos nativo de Odoo 18 (`combo_line_ids`), reemplazando la dependencia anterior del módulo Webkul POS Combo.

Los items del combo se muestran indentados debajo del producto principal con su cantidad correspondiente, manteniendo el orden original de comandeo (sin reordenar por categoría).

### 2. Encabezado personalizado
Reemplaza el encabezado estándar de la comanda:

- **Antes:** `T20 #589 👤 Usuario del sistema`
- **Ahora:** `MESA 20 - SALON PRINCIPAL 👤 Nombre del mesero`

Cambios específicos:
- `T20` → `MESA 20 - [nombre de la zona/piso]`
- `#589` (tracking number) → eliminado
- Campo `responsible` (usuario que creó la orden) → campo `waiter_name` del módulo `pos_table_time_waiter_tracker`

### 3. Orden original de productos
Las líneas de la comanda mantienen el orden en que fueron comandadas por el mesero, en lugar del ordenamiento por categoría que aplica Odoo por defecto.

### 4. Debounce en pantalla táctil (fix doble click)
Agrega un debounce de 500ms al toque/click en las comandas de la pantalla de preparación. Esto previene un bug nativo de Odoo donde un doble tap accidental en una pantalla (ej: PIZZA) podía resetear la etapa de la misma orden en otra pantalla (ej: COCINA), devolviéndola al estado POR PREPARAR.

## Dependencias

- `point_of_sale`
- `pos_preparation_display`
- `pos_restaurant_preparation_display`
- `pos_table_time_waiter_tracker`

## Estructura de archivos

```
screen_order_custom/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── pos_order.py                    # Override _process_preparation_changes (combo nativo)
│   ├── preparation_display_order.py    # Agrega floor_name y waiter_name al frontend
│   └── preparation_display_orderline.py # Campo pos_combo_list
└── static/src/app/
    ├── models/
    │   ├── order.js                    # Patch para recibir waiter_name
    │   ├── orderline.js                # OrderlineCustom con parseo de combo list
    │   └── preparation_display.js      # Usa OrderlineCustom en processOrders
    └── components/
        ├── order.js                    # Mantiene orden original de comandeo
        ├── order/order_click.js        # Debounce 500ms anti doble click
        ├── order/order.xml             # Template encabezado (MESA + zona, waiter_name)
        └── orderline/orderline.xml     # Template items combo indentados
```

## Historial de versiones

- **v1.0** — Versión original con soporte dual Webkul + combo nativo
- **v2.0** — Eliminada dependencia de Webkul, solo combo nativo
- **v3.0** — Encabezado personalizado (MESA + zona + waiter_name)
- **v4.0** — Versión consolidada con pos_order.py corregido y limpieza general
- **v5.0** — Fix debounce doble click en pantalla táctil (previene reset de etapa entre pantallas)
