"""
Knowledge base for the KTI-POS chatbot.

Provides structured system guides so the chatbot can answer
"how-to" questions without needing to call database tools.
Sections are assembled per user role (ADMIN gets everything,
VENTAS gets a subset).
"""

# ──────────────────────────────────────────────
# Sections visible to ALL roles
# ──────────────────────────────────────────────

KNOWLEDGE_NAVIGATION = """\
## NAVEGACIÓN DEL SISTEMA

El menú lateral (sidebar) tiene las siguientes secciones:

| Módulo | Ruta | Quién accede |
|--------|------|--------------|
| Dashboard | Inicio | Todos |
| Ventas | /sales | Todos |
| Productos | /products | Todos |
| Clientes | /clients | Todos |
| Inventario | /inventory | Solo ADMIN |
| Compras | /purchase-orders | Solo ADMIN |
| Envío SUNAT | /sunat | Solo ADMIN |
| Reportes | /reports | Solo ADMIN |
| Usuarios | /users | Solo ADMIN |
| Configuración | /settings | Solo ADMIN |

- El sidebar se puede colapsar haciendo clic en el ícono de menú.
- Arriba a la derecha hay un menú de usuario (cerrar sesión) y un botón para cambiar tema claro/oscuro.
"""

KNOWLEDGE_BUSINESS_RULES = """\
## REGLAS DE NEGOCIO GENERALES

- **IGV**: 18% incluido en todos los precios. El sistema calcula automáticamente: \
Op. Gravada = Total / 1.18, IGV = Total - Op. Gravada.
- **Moneda**: Soles (S/). Las compras también soportan dólares con tipo de cambio.
- **Tipos de documento de cliente**: DNI (8 dígitos), RUC (11 dígitos), NONE (público general).
- **FACTURA requiere cliente con RUC**. Si el cliente tiene DNI o NONE, solo se puede emitir BOLETA.
- **Métodos de pago**: EFECTIVO (el sistema calcula vuelto) o TARJETA.
- **Condiciones de pago**: CONTADO, CREDITO_30, CREDITO_60.
- **Stock se descuenta al guardar la PREVENTA**, no al facturar.
- **Stock se devuelve** si la venta se ANULA o ELIMINA.
"""

KNOWLEDGE_SALES = """\
## VENTAS — GUÍA COMPLETA

### Estados de una venta
- **PREVENTA** (azul): Borrador. Se puede editar, eliminar o facturar.
- **FACTURADO** (verde): Facturada/con boleta. Se puede anular.
- **ANULADO** (rojo): Anulada. No se puede modificar.

### Crear una venta paso a paso
1. Ve a **Ventas** en el menú lateral.
2. Haz clic en **"Nueva Venta"**.
3. Completa los campos del encabezado:
   - **Tipo/Serie**: Selecciona BOLETA o FACTURA y la serie (ej: B005, F001).
   - **Cliente**: Busca por nombre o número de documento. Para FACTURA, el cliente DEBE tener RUC.
   - **Almacén**: Selecciona el almacén de donde sale la mercadería.
   - **Vendedor**: Selecciona el vendedor responsable.
   - **Condición de pago**: CONTADO, CREDITO_30 o CREDITO_60.
   - **Máx. Dcto %**: Descuento máximo permitido por línea.
   - **Pago**: EFECTIVO (ingresa monto recibido, calcula vuelto) o TARJETA.
4. **Agrega productos**:
   - Busca por código o nombre en el campo de búsqueda.
   - El sistema muestra stock disponible (verde=ok, naranja=bajo, rojo=agotado).
   - Productos sin stock están deshabilitados.
   - Ingresa cantidad, precio unitario y % descuento por línea.
   - Si la cantidad excede el stock, la fila se resalta en amarillo como advertencia.
5. Revisa el **panel de resumen** (derecha): Op. Gravada, IGV 18%, TOTAL.
6. Elige una acción:
   - **"Guardar como PreVenta"**: Cualquier usuario puede hacerlo. Guarda como borrador.
   - **"Facturar"**: Solo ADMIN. Guarda, genera documento y envía a SUNAT automáticamente.

### Facturar una preventa existente
1. En la lista de ventas, busca la venta con estado PREVENTA.
2. Haz clic en el ícono de **editar** (lápiz).
3. Revisa los datos y haz clic en **"Facturar"** (solo ADMIN).
4. El sistema envía a SUNAT y muestra el resultado: ACEPTADO, PENDIENTE o ERROR.
5. Se abre la vista de impresión en una nueva pestaña.

### Anular una venta
1. Solo un **ADMIN** puede anular.
2. En la lista de ventas, busca la venta (PREVENTA o FACTURADO).
3. Haz clic en el ícono de **anular** (X).
4. Se abre un modal pidiendo el **motivo de anulación** (obligatorio).
5. Confirma. El estado cambia a ANULADO y el stock se devuelve.
6. Si era FACTURADO, además debes enviar una **comunicación de baja** a SUNAT \
(ve a Envío SUNAT > Bajas).

### Eliminar una preventa
- Solo ADMIN, solo si el estado es PREVENTA.
- Haz clic en el ícono de **eliminar** (papelera) y confirma.

### Filtros en la lista de ventas
- Rango de fechas, tipo de documento, almacén, vendedor, estado (multi-selección).
- Columnas: Fecha, Documento, Cliente, SubTotal, IGV, Total, Condición, Vendedor, Estado, SUNAT.
"""

KNOWLEDGE_PRODUCTS = """\
## PRODUCTOS

### Ver productos
- Ve a **Productos** en el menú lateral.
- Usa la barra de búsqueda para buscar por código o nombre.
- Filtra por **marca** o **categoría** con los dropdowns.

### Información de cada producto
- **Código**: SKU interno.
- **Nombre**: Nombre del producto.
- **Marca / Categoría**: Clasificación.
- **Presentación**: Empaque (ej: "Caja x 12").
- **P.V.P** (unit_price): Precio de venta al público.
- **P.MAY** (wholesale_price): Precio mayorista (opcional).
- **Costo** (cost_price): Precio de costo (solo visible para ADMIN).
- **Stock mínimo**: Nivel que activa alertas de stock bajo.
- **Stock total**: Suma de stock en todos los almacenes.

### Estados del producto
- **Activo** (verde): Disponible para venta.
- **Agotado** (rojo): Stock = 0 y sin pedido pendiente.
- **En Pedido** (naranja): Stock = 0 pero hay una orden de compra pendiente (muestra cantidad y ETA).
- **Inactivo** (rojo): Desactivado.

### Crear o editar un producto (solo ADMIN)
1. Haz clic en **"Nuevo Producto"** o en el ícono de editar.
2. Completa: Código, Nombre, Marca, Categoría, Presentación, Stock mínimo.
3. Ingresa precios: Costo, P.V.P, P.MAY (con prefijo S/).
4. Opcionalmente agrega un comentario.
5. Guarda.

### Editar stock rápido (solo ADMIN)
- En la lista de productos, haz clic sobre el número de stock para editarlo directamente.
"""

KNOWLEDGE_CLIENTS = """\
## CLIENTES

### Buscar clientes
- Ve a **Clientes** en el menú lateral.
- Busca por razón social o número de documento.

### Crear un cliente (solo ADMIN)
1. Haz clic en **"Nuevo Cliente"**.
2. **Pestaña "Datos Personales"**:
   - Selecciona tipo de documento: DNI, RUC o NONE.
   - Ingresa el número de documento.
   - **Consulta automática**: Si es RUC (11 dígitos), haz clic en "Consultar SUNAT" para \
auto-completar razón social y dirección. Si es DNI (8 dígitos), "Consultar RENIEC" auto-completa el nombre.
   - Completa: Razón social, referencia comercial, teléfono, email, comentario.
3. **Pestaña "Dirección"**: Dirección completa y zona.
4. **Pestaña "Crédito"**: Límite de crédito (S/) y días de crédito.
5. Guarda.

### Regla importante
- Para emitir **FACTURA**, el cliente DEBE tener tipo de documento **RUC**. \
Si el cliente tiene DNI o NONE, solo se puede emitir BOLETA.
"""

KNOWLEDGE_TROUBLESHOOTING = """\
## SOLUCIÓN DE PROBLEMAS COMUNES

| Problema | Causa | Solución |
|----------|-------|----------|
| "No puedo crear factura" | El cliente no tiene RUC | Cambia el tipo de documento a BOLETA, o edita el cliente y agrega su RUC |
| "No puedo facturar" | No tienes rol ADMIN, o la venta no está en PREVENTA | Pide a un ADMIN que facture, o verifica que el estado sea PREVENTA |
| "Stock insuficiente" | No hay stock en el almacén seleccionado | Revisa otros almacenes en Inventario, o crea una orden de compra |
| "No veo costos ni utilidad" | Tienes rol VENTAS | Solo ADMIN puede ver precios de costo y reportes de utilidad |
| "No puedo editar la venta" | La venta ya fue FACTURADA o ANULADA | Solo se pueden editar ventas en estado PREVENTA |
| "No puedo eliminar la venta" | No eres ADMIN o la venta no es PREVENTA | Solo ADMIN puede eliminar, y solo preventas |
| "SUNAT devolvió error" | Error en el envío electrónico | Ve a Envío SUNAT > Facturas, revisa el error y haz clic en "Reenviar" |
| "No aparece el producto" | Puede estar inactivo o el nombre es diferente | Busca con términos más amplios o revisa si está marcado como inactivo |
| "No puedo acceder a Inventario/Reportes/Compras" | Tienes rol VENTAS | Estas secciones son exclusivas para ADMIN |
"""

# ──────────────────────────────────────────────
# Sections visible ONLY to ADMIN
# ──────────────────────────────────────────────

KNOWLEDGE_INVENTORY = """\
## INVENTARIO (solo ADMIN)

### Ver stock
1. Ve a **Inventario** en el menú lateral.
2. Filtra por almacén o activa **"Solo stock bajo"** para ver productos bajo el mínimo.
3. Columnas: Código, Producto, Almacén, Cantidad, Estado (Stock Bajo / Normal).

### Ajustar stock
1. En Inventario, haz clic en **"Ajustar Stock"**.
2. Selecciona producto, almacén, ingresa la nueva cantidad y una nota explicativa.
3. Guarda. Se crea un movimiento tipo ADJUSTMENT en el historial.

### Ver movimientos
1. Ve a **Inventario > Movimientos**.
2. Filtra por producto, almacén o tipo de movimiento.
3. Tipos: SALE (venta), PURCHASE (compra), ADJUSTMENT (ajuste manual), \
TRANSFER_IN (entrada por transferencia), TRANSFER_OUT (salida por transferencia).
4. Cada movimiento muestra: fecha, producto, almacén, tipo, cantidad (+verde/-rojo), \
referencia (ej: SALE #123), y notas.

### Alertas de stock bajo
1. Ve a **Inventario > Alertas**.
2. Muestra automáticamente productos cuyo stock está por debajo del mínimo configurado.
3. También aparece un contador en el Dashboard ("Stock Bajo").
"""

KNOWLEDGE_PURCHASES = """\
## COMPRAS / ÓRDENES DE COMPRA (solo ADMIN)

### Estados
- **DRAFT**: Borrador, se puede editar, recibir o eliminar.
- **RECEIVED**: Recibida, bloqueada. El stock ya fue actualizado.
- **CANCELLED**: Cancelada, bloqueada.

### Crear una orden de compra
1. Ve a **Compras** y haz clic en **"Nueva Orden"**.
2. Completa el encabezado:
   - **Tipo documento**: FACTURA o BOLETA del proveedor.
   - **Proveedor**: Busca por RUC o nombre.
   - **Condición**: CONTADO o CRÉDITO.
   - **Moneda**: SOLES o DÓLARES (si dólares, ingresa tipo de cambio).
   - **IGV**: "Con IGV" (precios incluyen impuesto) o "Sin IGV" (se agrega).
   - **Flete**: Costo total de transporte.
   - **GRR**: Número de guía de remisión.
   - **Fecha entrega esperada**: ETA.
3. **Agrega productos**:
   - Selecciona producto, cantidad, costo unitario.
   - Opcionalmente aplica hasta **3 descuentos en cascada** (ej: 10%, 5%, 2% = se aplican secuencialmente).
   - Flete por unidad (opcional).
   - El total por línea se calcula: qty × (costo × (1-d1%) × (1-d2%) × (1-d3%)) + qty × flete_unit.
4. Revisa totales: Op. Gravada, IGV, Total.
5. Guarda como DRAFT.

### Recibir una orden de compra
1. En la lista de compras, busca la orden en estado DRAFT.
2. Haz clic en el ícono de **recibir** (check ✓).
3. Confirma: "¿Recibir orden? Esto actualizará el stock."
4. El estado cambia a RECEIVED.
5. El stock se actualiza automáticamente en el almacén.
6. Se crean movimientos tipo PURCHASE en el historial de inventario.
"""

KNOWLEDGE_SUNAT = """\
## ENVÍO SUNAT (solo ADMIN)

### Panel SUNAT — 3 pestañas

#### Pestaña 1: Facturas
- Muestra todas las facturas enviadas a SUNAT con su estado.
- **Estados SUNAT**: ACEPTADO (verde), PENDIENTE (naranja), ERROR/RECHAZADO (rojo).
- **Acciones**: Reenviar (si no fue aceptada), descargar PDF, XML, CDR.
- Si una factura tiene ERROR, haz clic en **"Reenviar"** para reintentar.

#### Pestaña 2: Resumen de Boletas
- SUNAT requiere un resumen diario de todas las boletas del día.
- **Flujo**:
  1. Selecciona la fecha.
  2. El sistema muestra las boletas facturadas y anuladas de ese día.
  3. Haz clic en **"Enviar Resumen Diario"**.
  4. Resultado: ACEPTADO, o PENDIENTE con un número de ticket.
  5. Si queda PENDIENTE, haz clic en **"Consultar"** para verificar el estado del ticket.

#### Pestaña 3: Bajas (Comunicación de Baja)
- Se usa para notificar a SUNAT cuando se anula una **factura** (las boletas se anulan vía resumen).
- **Flujo**:
  1. Anula la venta primero (desde la lista de ventas).
  2. Ve a SUNAT > Bajas.
  3. Selecciona la factura anulada.
  4. Ingresa el motivo (por defecto: "ANULACION DE OPERACION").
  5. Envía. Resultado: ACEPTADO o PENDIENTE con ticket.
  6. Consulta el ticket si queda pendiente.
"""

KNOWLEDGE_REPORTS = """\
## REPORTES (solo ADMIN)

### Dashboard (página de inicio)
- **Ventas Hoy**: Cantidad de ventas del día.
- **Total Hoy**: Monto total facturado hoy.
- **Ventas del Mes**: Cantidad de ventas del mes.
- **Stock Bajo**: Cantidad de productos bajo el mínimo.

### Reporte 1: Ventas por Período
1. Ve a **Reportes** > pestaña "Ventas por Período".
2. Selecciona rango de fechas y agrupación (Día, Semana, Mes).
3. Muestra gráfico de barras + tabla con: Período, # Ventas, Total.

### Reporte 2: Top Productos
1. Pestaña "Top Productos".
2. Selecciona rango de fechas y límite (1-100).
3. Muestra ranking: Producto, Cantidad Vendida, Ingresos.

### Reporte 3: Reporte de Utilidades
1. Pestaña "Reporte de Utilidades".
2. Selecciona rango de fechas.
3. Muestra: Código, Artículo, Marca, Cant. Total, Importe Venta, Costo Total, \
Utilidad Total, % Rentabilidad.
4. Colores de rentabilidad: rojo (<10%), naranja (10-20%), verde (≥20%).
5. Puedes **exportar a CSV** con el botón "Exportar".
"""

KNOWLEDGE_USERS = """\
## GESTIÓN DE USUARIOS (solo ADMIN)

### Roles
- **ADMIN**: Acceso completo a todo el sistema.
- **VENTAS**: Solo accede a Ventas, Productos y Clientes. No ve costos ni utilidad.

### Crear usuario
1. Ve a **Usuarios** y haz clic en "Nuevo Usuario".
2. Ingresa: Nombre de usuario (login), contraseña, nombre completo, rol (ADMIN o VENTAS).
3. Guarda.

### Editar usuario
- Puedes cambiar nombre completo y rol. El nombre de usuario no se puede cambiar.

### Cambiar contraseña
- Haz clic en el ícono de llave junto al usuario.
- Ingresa nueva contraseña y confirmación (mínimo 6 caracteres).

### Desactivar usuario
- Haz clic en eliminar (papelera). Esto desactiva al usuario (no lo borra permanentemente).
"""

KNOWLEDGE_SETTINGS = """\
## CONFIGURACIÓN (solo ADMIN)

La página de Configuración tiene 5 pestañas:

### 1. Marcas
- Crear, editar o eliminar marcas de productos.
- Campos: Nombre, Estado (activo/inactivo).

### 2. Categorías
- Crear, editar o eliminar categorías de productos.
- Campos: Nombre, Estado (activo/inactivo).

### 3. Almacenes
- Crear, editar o eliminar almacenes.
- Campos: Nombre, Dirección (opcional), Estado.
- El stock se trackea por almacén (cada producto tiene stock independiente en cada almacén).

### 4. Proveedores
- Crear, editar o eliminar proveedores para órdenes de compra.
- Campos: RUC, Razón Social, Ciudad, Teléfono, Email, Dirección.
- Si ingresas un RUC de 11 dígitos, puedes hacer **"Consultar SUNAT"** para auto-completar datos.

### 5. Series de Documentos
- Configurar series para BOLETA y FACTURA (ej: B005, F001).
- Campos: Tipo documento, Serie, Siguiente número (auto-incrementa con cada venta).
- Las series no se pueden eliminar.
- Cada tipo/serie tiene su propia numeración independiente.
"""


def build_knowledge_base(role: str) -> str:
    """Assemble the knowledge base sections appropriate for the user's role.

    ADMIN gets all sections; VENTAS gets only the sections they can access.
    """
    # Sections visible to all roles
    sections = [
        KNOWLEDGE_NAVIGATION,
        KNOWLEDGE_BUSINESS_RULES,
        KNOWLEDGE_SALES,
        KNOWLEDGE_PRODUCTS,
        KNOWLEDGE_CLIENTS,
        KNOWLEDGE_TROUBLESHOOTING,
    ]

    # Admin-only sections
    if role == "ADMIN":
        sections.extend([
            KNOWLEDGE_INVENTORY,
            KNOWLEDGE_PURCHASES,
            KNOWLEDGE_SUNAT,
            KNOWLEDGE_REPORTS,
            KNOWLEDGE_USERS,
            KNOWLEDGE_SETTINGS,
        ])

    header = "# GUÍA DE USO DEL SISTEMA KTI POS\n\n"
    return header + "\n".join(sections)
