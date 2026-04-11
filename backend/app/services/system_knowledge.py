"""
Base de conocimiento para el chatbot de KTI-POS.

Provee guías estructuradas del sistema para que el chatbot pueda responder
preguntas tipo "cómo hacer" sin necesidad de llamar herramientas de base de datos.
Las secciones se ensamblan según el rol del usuario (ADMIN obtiene todo,
VENTAS obtiene un subconjunto).
"""

# ──────────────────────────────────────────────
# Secciones visibles para TODOS los roles
# ──────────────────────────────────────────────

KNOWLEDGE_NAVIGATION = """\
## NAVEGACIÓN DEL SISTEMA

La barra lateral tiene las siguientes secciones:

| Módulo | Ruta | Quién puede acceder |
|--------|------|---------------------|
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

- La barra lateral se puede colapsar haciendo clic en el ícono de menú.
- Arriba a la derecha hay un menú de usuario (cerrar sesión) y un botón para cambiar entre tema claro/oscuro.
"""

KNOWLEDGE_BUSINESS_RULES = """\
## REGLAS GENERALES DEL NEGOCIO

- **IGV**: 18% incluido en todos los precios. El sistema calcula automáticamente: \
Op. Gravada = Total / 1.18, IGV = Total - Op. Gravada.
- **Moneda**: Soles peruanos (S/). Las compras también soportan dólares con tipo de cambio.
- **Tipos de documento de cliente**: DNI (8 dígitos), RUC (11 dígitos), NINGUNO (público general).
- **FACTURA requiere un cliente con RUC**. Si el cliente tiene DNI o NINGUNO, solo se puede emitir BOLETA.
- **Métodos de pago**: EFECTIVO (el sistema calcula el vuelto) o TARJETA.
- **Condiciones de pago**: CONTADO, CREDITO_30, CREDITO_60.
- **El stock se descuenta cuando se guarda la PREVENTA**, no cuando se factura.
- **El stock se devuelve** si la venta es ANULADA o ELIMINADA.
"""

KNOWLEDGE_SALES = """\
## VENTAS — GUÍA COMPLETA

### Estados de venta
- **PREVENTA** (azul): Borrador. Se puede editar, eliminar o facturar.
- **FACTURADO** (verde): Facturado (boleta o factura). Se puede anular.
- **ANULADO** (rojo): Anulado. No se puede modificar.

### Crear una venta paso a paso
1. Ve a **Ventas** en la barra lateral.
2. Haz clic en **"Nueva Venta"**.
3. Llena los campos del encabezado:
   - **Tipo/Serie**: Selecciona BOLETA o FACTURA y la serie (ej: B005, F001).
   - **Cliente**: Busca por nombre o número de documento. Para FACTURA, el cliente DEBE tener RUC.
   - **Almacén**: Selecciona el almacén de donde sale la mercadería.
   - **Vendedor**: Selecciona el vendedor responsable.
   - **Condición de pago**: CONTADO, CREDITO_30 o CREDITO_60.
   - **% Descuento Máximo**: Descuento máximo permitido por línea.
   - **Pago**: EFECTIVO (ingresa el monto recibido, calcula vuelto) o TARJETA.
4. **Agregar productos**:
   - Busca por código o nombre en el campo de búsqueda.
   - El sistema muestra el stock disponible (verde=ok, naranja=bajo, rojo=agotado).
   - Los productos sin stock están deshabilitados.
   - Ingresa cantidad, precio unitario y % de descuento por línea.
   - Si la cantidad excede el stock, la fila se resalta en amarillo como advertencia.
5. Revisa el **panel de resumen** (derecha): Op. Gravada, IGV 18%, TOTAL.
6. Elige una acción:
   - **"Guardar como PreVenta"**: Cualquier usuario puede hacerlo. Guarda como borrador.
   - **"Facturar"**: Solo ADMIN. Guarda, genera el documento y envía a SUNAT automáticamente.

### Facturar una preventa existente
1. En la lista de ventas, busca la venta con estado PREVENTA.
2. Haz clic en el ícono de **editar** (lápiz).
3. Revisa los datos y haz clic en **"Facturar"** (solo ADMIN).
4. El sistema envía a SUNAT y muestra el resultado: ACEPTADO, PENDIENTE o ERROR.
5. La vista de impresión se abre en una nueva pestaña.

### Anular una venta
1. Solo un **ADMIN** puede anular.
2. En la lista de ventas, busca la venta (PREVENTA o FACTURADO).
3. Haz clic en el ícono de **anular** (X).
4. Se abre un modal pidiendo el **motivo de anulación** (obligatorio).
5. Confirma. El estado cambia a ANULADO y el stock se devuelve.
6. Si era FACTURADO, también debes enviar una **comunicación de baja** a SUNAT \
(ve a Envío SUNAT > Bajas).

### Eliminar una preventa
- Solo ADMIN, solo si el estado es PREVENTA.
- Haz clic en el ícono de **eliminar** (basura) y confirma.

### Filtros en la lista de ventas
- Rango de fechas, tipo de documento, almacén, vendedor, estado (selección múltiple).
- Columnas: Fecha, Documento, Cliente, SubTotal, IGV, Total, Condición, Vendedor, Estado, SUNAT.
"""

KNOWLEDGE_PRODUCTS = """\
## PRODUCTOS

### Ver productos
- Ve a **Productos** en la barra lateral.
- Usa la barra de búsqueda para buscar por código o nombre.
- Filtra por **marca** o **categoría** con los selectores.

### Información de cada producto
- **Código**: SKU interno.
- **Nombre**: Nombre del producto.
- **Marca / Categoría**: Clasificación.
- **Presentación**: Empaque (ej: "Caja de 12").
- **P.V.P** (unit_price): Precio al público.
- **P.MAY** (wholesale_price): Precio mayorista (opcional).
- **Costo** (cost_price): Precio de costo (visible solo para ADMIN).
- **Stock mínimo**: Nivel que dispara las alertas de stock bajo.
- **Stock total**: Suma del stock en todos los almacenes.

### Estados de producto
- **Activo** (verde): Disponible para vender.
- **Sin stock** (rojo): Stock = 0 y sin orden pendiente.
- **En Pedido** (naranja): Stock = 0 pero hay una orden de compra pendiente (muestra cantidad y ETA).
- **Inactivo** (rojo): Deshabilitado.

### Crear o editar un producto (solo ADMIN)
1. Haz clic en **"Nuevo Producto"** o el ícono de editar.
2. Llena: Código, Nombre, Marca, Categoría, Presentación, Stock mínimo.
3. Ingresa precios: Costo, P.V.P, P.MAY (con prefijo S/).
4. Opcionalmente agrega un comentario.
5. Guarda.

### Edición rápida de stock (solo ADMIN)
- En la lista de productos, haz clic en el número de stock para editarlo directamente.
"""

KNOWLEDGE_CLIENTS = """\
## CLIENTES

### Buscar clientes
- Ve a **Clientes** en la barra lateral.
- Busca por razón social o número de documento.

### Crear un cliente (solo ADMIN)
1. Haz clic en **"Nuevo Cliente"**.
2. **Pestaña "Datos Personales"**:
   - Selecciona el tipo de documento: DNI, RUC o NINGUNO.
   - Ingresa el número de documento.
   - **Búsqueda automática**: Si es RUC (11 dígitos), haz clic en "Consultar SUNAT" para \
autocompletar razón social y dirección. Si es DNI (8 dígitos), "Consultar RENIEC" autocompleta el nombre.
   - Llena: Razón social, referencia comercial, teléfono, email, comentario.
3. **Pestaña "Dirección"**: Dirección completa y zona.
4. **Pestaña "Crédito"**: Límite de crédito (S/) y días de crédito.
5. Guarda.

### Regla importante
- Para emitir una **FACTURA**, el cliente DEBE tener tipo de documento **RUC**. \
Si el cliente tiene DNI o NINGUNO, solo se puede emitir BOLETA.
"""

KNOWLEDGE_TROUBLESHOOTING = """\
## SOLUCIÓN DE PROBLEMAS COMUNES

| Problema | Causa | Solución |
|----------|-------|----------|
| "No puedo crear una factura" | El cliente no tiene RUC | Cambia el tipo de documento a BOLETA, o edita el cliente y agrega su RUC |
| "No puedo facturar" | No tienes el rol ADMIN, o la venta no está en PREVENTA | Pide a un ADMIN que facture, o verifica que el estado sea PREVENTA |
| "Stock insuficiente" | No hay stock en el almacén seleccionado | Revisa otros almacenes en Inventario, o crea una orden de compra |
| "No puedo ver costos ni utilidad" | Tienes el rol VENTAS | Solo ADMIN puede ver precios de costo y reportes de utilidad |
| "No puedo editar la venta" | La venta ya está FACTURADA o ANULADA | Solo se pueden editar ventas en PREVENTA |
| "No puedo eliminar la venta" | No eres ADMIN o la venta no está en PREVENTA | Solo ADMIN puede eliminar, y solo preventas |
| "SUNAT devolvió un error" | Error en el envío electrónico | Ve a Envío SUNAT > Facturas, revisa el error y haz clic en "Reenviar" |
| "El producto no aparece" | Puede estar inactivo o el nombre es diferente | Busca con términos más amplios o revisa si está marcado como inactivo |
| "No puedo acceder a Inventario/Reportes/Compras" | Tienes el rol VENTAS | Estas secciones son exclusivas para ADMIN |
"""

# ──────────────────────────────────────────────
# Secciones visibles SOLO para ADMIN
# ──────────────────────────────────────────────

KNOWLEDGE_INVENTORY = """\
## INVENTARIO (solo ADMIN)

### Ver stock
1. Ve a **Inventario** en la barra lateral.
2. Filtra por almacén o activa **"Solo stock bajo"** para ver productos por debajo del mínimo.
3. Columnas: Código, Producto, Almacén, Cantidad, Estado (Stock Bajo / Normal).

### Ajustar stock
1. En Inventario, haz clic en **"Ajustar Stock"**.
2. Selecciona producto, almacén, ingresa la nueva cantidad y una nota explicativa.
3. Guarda. Se crea un movimiento tipo AJUSTE en el historial.

### Ver movimientos
1. Ve a **Inventario > Movimientos**.
2. Filtra por producto, almacén o tipo de movimiento.
3. Tipos: VENTA, COMPRA, AJUSTE (ajuste manual), \
TRANSFERENCIA_ENTRADA, TRANSFERENCIA_SALIDA.
4. Cada movimiento muestra: fecha, producto, almacén, tipo, cantidad (+verde/-rojo), \
referencia (ej: VENTA #123), y notas.

### Alertas de stock bajo
1. Ve a **Inventario > Alertas**.
2. Muestra automáticamente los productos cuyo stock está por debajo del mínimo configurado.
3. También aparece un contador en el Dashboard ("Stock Bajo").
"""

KNOWLEDGE_PURCHASES = """\
## COMPRAS / ÓRDENES DE COMPRA (solo ADMIN)

### Estados
- **DRAFT** (Borrador): Se puede editar, recibir o eliminar.
- **RECEIVED** (Recibido): Bloqueado. El stock ya fue actualizado.
- **CANCELLED** (Cancelado): Bloqueado.

### Crear una orden de compra
1. Ve a **Compras** y haz clic en **"Nueva Orden"**.
2. Llena el encabezado:
   - **Tipo de documento**: FACTURA, BOLETA o NOTA DE VENTA del proveedor.
   - **Proveedor**: Busca por RUC o nombre.
   - **Condición**: CONTADO o CRÉDITO.
   - **Moneda**: SOLES o DÓLARES (si es dólares, ingresa el tipo de cambio).
   - **IGV**: "Con IGV" (los precios incluyen impuesto) o "Sin IGV" (se agrega).
   - **Flete**: Costo total de transporte.
   - **GRR**: Número de guía de remisión.
   - **Fecha estimada de entrega**: ETA.
3. **Agregar productos**:
   - Selecciona producto, cantidad, costo unitario.
   - Opcionalmente aplica hasta **3 descuentos en cascada** (ej: 10%, 5%, 2% = aplicados secuencialmente).
   - Flete por unidad (opcional).
   - El total de línea se calcula: cant × (costo × (1-d1%) × (1-d2%) × (1-d3%)) + cant × flete_unit.
4. Revisa los totales: Op. Gravada, IGV, Total.
5. Guarda como BORRADOR.

### Recibir una orden de compra
1. En la lista de compras, busca la orden en estado BORRADOR.
2. Haz clic en el ícono de **recibir** (check ✓).
3. Confirma: "¿Recibir orden? Esto actualizará el stock."
4. El estado cambia a RECIBIDO.
5. El stock se actualiza automáticamente en el almacén.
6. Se crean movimientos tipo COMPRA en el historial de inventario.
"""

KNOWLEDGE_SUNAT = """\
## ENVÍO SUNAT (solo ADMIN)

### Panel SUNAT — pestañas

#### Pestaña 1: Facturas
- Muestra todas las facturas enviadas a SUNAT con su estado.
- **Estados SUNAT**: ACEPTADO (verde), PENDIENTE (naranja), ERROR/RECHAZADO (rojo).
- **Acciones**: Reenviar (si no fue aceptada), descargar PDF, XML, CDR.
- Si una factura tiene ERROR, haz clic en **"Reenviar"** para reintentar.

#### Pestaña 2: Resumen Diario de Boletas
- SUNAT exige un resumen diario de todas las boletas del día.
- **Flujo**:
  1. Selecciona la fecha.
  2. El sistema muestra las boletas facturadas y anuladas de ese día.
  3. Haz clic en **"Enviar Resumen Diario"**.
  4. Resultado: ACEPTADO, o PENDIENTE con un número de ticket.
  5. Si está PENDIENTE, haz clic en **"Verificar"** para revisar el estado del ticket.

#### Pestaña 3: Notas de Crédito
- Notas de crédito para facturas (F-series), enviadas individualmente vía sendBill.
- Las NC para boletas (B-series) se envían en el Resumen Diario, no aquí.

#### Pestaña 4: Bajas (Comunicación de Baja)
- Se usa para notificar a SUNAT cuando una **factura** es anulada (las boletas se anulan vía resumen).
- **Flujo**:
  1. Anula la venta primero (desde la lista de ventas).
  2. Ve a SUNAT > Bajas.
  3. Selecciona la factura anulada.
  4. Ingresa el motivo (por defecto: "ANULACION DE OPERACION").
  5. Envía. Resultado: ACEPTADO o PENDIENTE con ticket.
  6. Verifica el ticket si queda pendiente.
"""

KNOWLEDGE_REPORTS = """\
## REPORTES (solo ADMIN)

### Dashboard (página de inicio)
- **Ventas Hoy**: Número de ventas del día.
- **Total Hoy**: Total facturado hoy.
- **Ventas del Mes**: Número de ventas del mes.
- **Stock Bajo**: Número de productos por debajo del mínimo.

### Reporte 1: Ventas por Período
1. Ve a **Reportes** > pestaña "Ventas por Período".
2. Selecciona rango de fechas y agrupación (Día, Semana, Mes).
3. Muestra gráfico de barras + tabla con: Período, # Ventas, Total.

### Reporte 2: Top Productos
1. Pestaña "Top Productos".
2. Selecciona rango de fechas y límite (1-100).
3. Muestra ranking: Producto, Cantidad Vendida, Ingresos.

### Reporte 3: Reporte de Utilidad
1. Pestaña "Reporte de Utilidad".
2. Selecciona rango de fechas.
3. Muestra: Código, Item, Marca, Cant. Total, Monto Venta, Costo Total, \
Utilidad Total, % Rentabilidad.
4. Colores de rentabilidad: rojo (<10%), naranja (10-20%), verde (≥20%).
5. Puedes **exportar a CSV** con el botón "Exportar".
"""

KNOWLEDGE_USERS = """\
## GESTIÓN DE USUARIOS (solo ADMIN)

### Roles
- **ADMIN**: Acceso completo a todo el sistema.
- **VENTAS**: Solo accede a Ventas, Productos y Clientes. No puede ver costos ni utilidad.

### Crear un usuario
1. Ve a **Usuarios** y haz clic en "Nuevo Usuario".
2. Ingresa: Usuario (login), contraseña, nombre completo, rol (ADMIN o VENTAS).
3. Guarda.

### Editar un usuario
- Puedes cambiar el nombre completo y el rol. El usuario (login) no se puede cambiar.

### Cambiar contraseña
- Haz clic en el ícono de llave junto al usuario.
- Ingresa la nueva contraseña y confirmación (mínimo 6 caracteres).

### Desactivar usuario
- Haz clic en eliminar (basura). Esto desactiva al usuario (no lo borra permanentemente).
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
- El stock se controla por almacén (cada producto tiene stock independiente en cada almacén).

### 4. Proveedores
- Crear, editar o eliminar proveedores para órdenes de compra.
- Campos: RUC, Razón Social, Ciudad, Teléfono, Email, Dirección.
- Si ingresas un RUC de 11 dígitos, puedes hacer **"Consultar SUNAT"** para autocompletar los datos.

### 5. Series de Documentos
- Configura las series para BOLETA y FACTURA (ej: B005, F001).
- Campos: Tipo de documento, Serie, Próximo número (auto-incrementa con cada venta).
- Las series no se pueden eliminar.
- Cada tipo/serie tiene su propia numeración independiente.
"""


def build_knowledge_base(role: str) -> str:
    """Ensambla las secciones de la base de conocimiento apropiadas para el rol del usuario.

    ADMIN obtiene todas las secciones; VENTAS obtiene solo las secciones a las que puede acceder.
    """
    # Secciones visibles para todos los roles
    sections = [
        KNOWLEDGE_NAVIGATION,
        KNOWLEDGE_BUSINESS_RULES,
        KNOWLEDGE_SALES,
        KNOWLEDGE_PRODUCTS,
        KNOWLEDGE_CLIENTS,
        KNOWLEDGE_TROUBLESHOOTING,
    ]

    # Secciones solo para ADMIN
    if role == "ADMIN":
        sections.extend([
            KNOWLEDGE_INVENTORY,
            KNOWLEDGE_PURCHASES,
            KNOWLEDGE_SUNAT,
            KNOWLEDGE_REPORTS,
            KNOWLEDGE_USERS,
            KNOWLEDGE_SETTINGS,
        ])

    header = "# GUÍA DE USUARIO DEL SISTEMA KTI POS\n\n"
    return header + "\n".join(sections)
