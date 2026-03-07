import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.client import Client
from app.models.inventory import Inventory
from app.models.product import Brand, Category, Product
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.models.warehouse import Warehouse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Eres el asistente virtual de KTI POS, un sistema de punto de venta. \
Tu rol es ayudar a los usuarios a usar el sistema y consultar datos en tiempo real.

FUNCIONALIDADES DEL SISTEMA:
- Ventas: crear preventas, aprobar, facturar (boleta/factura), anular
- Productos: gestionar productos con código, marca, categoría, precios, stock mínimo
- Clientes: gestionar clientes con RUC/DNI, límite de crédito
- Inventario: ver stock por almacén, ajustes, transferencias, alertas de stock bajo
- Compras: órdenes de compra a proveedores
- SUNAT: envío electrónico de facturas y boletas
- Reportes: dashboard, ventas por período, productos top, rentabilidad (solo ADMIN)

FLUJO DE VENTA:
1. Crear preventa: seleccionar cliente, agregar productos, aplicar descuentos
2. Aprobar: cambia estado a APROBADA, descuenta stock
3. Facturar: genera boleta o factura electrónica
4. Opcionalmente enviar a SUNAT

REGLAS:
- Responde SIEMPRE en español
- Usa formato S/ para montos (ejemplo: S/ 125.50)
- NUNCA inventes datos, solo usa información real de las herramientas
- Si no encuentras datos, dilo claramente
- Sé conciso y directo
- Para saludos simples (hola, buenos días, etc.), responde amablemente SIN llamar herramientas
- Solo usa herramientas cuando el usuario pida datos específicos (productos, clientes, ventas, stock)
- {role_instruction}

TIPS DE BÚSQUEDA:
- Los usuarios pueden pedir productos por nombre coloquial (ej: "llanta duro") — "duro" es la MARCA, "llanta" el tipo
- Si buscas "llanta duro" y no encuentras, prueba: brand="duro" sin query, o query="llanta" sin brand
- La herramienta search_products busca en nombre, código Y marca. Puedes pasar solo query="duro" para encontrar productos de marca DURO
- Si no hay resultados, intenta búsquedas más amplias antes de decir que no existe
- Cuando muestres resultados, formatea como tabla o lista clara con código, nombre, marca, precio y stock
"""

VENTAS_INSTRUCTION = (
    "El usuario tiene rol VENTAS: NO puede ver precios de costo ni utilidad/ganancia. "
    "Si pregunta por costos o ganancias, indica que no tiene permisos."
)
ADMIN_INSTRUCTION = (
    "El usuario tiene rol ADMIN: puede ver toda la información incluyendo costos y ganancias."
)

# Tool declarations for Gemini function calling
TOOL_DECLARATIONS = [
    {
        "name": "search_products",
        "description": "Buscar productos por nombre, código o marca. Retorna lista con precios y stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar en nombre o código del producto",
                },
                "brand": {
                    "type": "string",
                    "description": "Filtrar por nombre de marca (búsqueda parcial)",
                },
                "category": {
                    "type": "string",
                    "description": "Filtrar por nombre de categoría (búsqueda parcial)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados (default 10)",
                },
            },
        },
    },
    {
        "name": "get_product_details",
        "description": "Obtener información detallada de un producto por su ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID del producto",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Consultar niveles de stock. Puede filtrar por producto, almacén, o solo stock bajo.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Filtrar por nombre de producto (búsqueda parcial)",
                },
                "warehouse_name": {
                    "type": "string",
                    "description": "Filtrar por nombre de almacén",
                },
                "low_stock_only": {
                    "type": "boolean",
                    "description": "Si true, solo muestra productos con stock por debajo del mínimo",
                },
            },
        },
    },
    {
        "name": "search_clients",
        "description": "Buscar clientes por nombre o número de documento (RUC/DNI).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar en nombre o número de documento",
                },
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados (default 10)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_client_details",
        "description": "Obtener información detallada de un cliente por su ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "integer",
                    "description": "ID del cliente",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "get_sales_summary",
        "description": "Obtener resumen de ventas: cantidad, total facturado. Puede filtrar por período y vendedor.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Período: 'today', 'week', 'month', 'year', o 'all' (default 'month')",
                },
                "seller_name": {
                    "type": "string",
                    "description": "Filtrar por nombre del vendedor",
                },
            },
        },
    },
    {
        "name": "search_sales",
        "description": "Buscar ventas recientes. Puede filtrar por cliente, producto, o rango de fechas.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {
                    "type": "string",
                    "description": "Filtrar por nombre del cliente",
                },
                "product_name": {
                    "type": "string",
                    "description": "Filtrar por nombre de producto en los items",
                },
                "from_date": {
                    "type": "string",
                    "description": "Fecha inicio (YYYY-MM-DD)",
                },
                "to_date": {
                    "type": "string",
                    "description": "Fecha fin (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados (default 10)",
                },
            },
        },
    },
]


# ─── Tool execution functions ───


def _exec_search_products(db: Session, args: dict, user_role: str) -> str:
    query = args.get("query", "")
    brand = args.get("brand", "")
    category = args.get("category", "")
    limit = min(args.get("limit", 10), 20)

    from sqlalchemy import or_

    base = (
        db.query(Product)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .filter(Product.is_active == True)  # noqa: E712
    )

    q = base

    if query and brand:
        # Both provided: name/code matches query AND brand matches
        q = q.filter(
            or_(Product.name.ilike(f"%{query}%"), Product.code.ilike(f"%{query}%"))
        )
        q = q.filter(Brand.name.ilike(f"%{brand}%"))
    elif query:
        # Search across name, code, AND brand name with OR
        q = q.filter(
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.code.ilike(f"%{query}%"),
                Brand.name.ilike(f"%{query}%"),
            )
        )
    elif brand:
        q = q.filter(Brand.name.ilike(f"%{brand}%"))

    if category:
        q = q.filter(Category.name.ilike(f"%{category}%"))

    products = q.limit(limit).all()

    # Fallback: if no results and multiple words, try each word separately
    if not products and query and " " in query:
        words = query.split()
        conditions = []
        for word in words:
            conditions.append(Product.name.ilike(f"%{word}%"))
            conditions.append(Product.code.ilike(f"%{word}%"))
            conditions.append(Brand.name.ilike(f"%{word}%"))
        q = base.filter(or_(*conditions))
        if category:
            q = q.filter(Category.name.ilike(f"%{category}%"))
        products = q.limit(limit).all()

    results = []
    for p in products:
        # Get total stock
        total_stock = (
            db.query(sa_func.coalesce(sa_func.sum(Inventory.quantity), 0))
            .filter(Inventory.product_id == p.id)
            .scalar()
        )
        item = {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "brand": p.brand.name if p.brand else None,
            "category": p.category.name if p.category else None,
            "unit_price": f"{p.unit_price:.2f}",
            "wholesale_price": f"{p.wholesale_price:.2f}" if p.wholesale_price else None,
            "stock_total": int(total_stock),
        }
        if user_role == "ADMIN" and p.cost_price is not None:
            item["cost_price"] = f"{p.cost_price:.2f}"
        results.append(item)

    return json.dumps(results, ensure_ascii=False)


def _exec_get_product_details(db: Session, args: dict, user_role: str) -> str:
    product_id = args.get("product_id")
    p = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()  # noqa: E712
    if not p:
        return json.dumps({"error": "Producto no encontrado"})

    # Stock by warehouse
    inv_rows = (
        db.query(Inventory, Warehouse)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .filter(Inventory.product_id == p.id)
        .all()
    )
    stock_detail = [
        {"warehouse": w.name, "quantity": inv.quantity} for inv, w in inv_rows
    ]

    result = {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "brand": p.brand.name if p.brand else None,
        "category": p.category.name if p.category else None,
        "presentation": p.presentation,
        "unit_price": f"{p.unit_price:.2f}",
        "wholesale_price": f"{p.wholesale_price:.2f}" if p.wholesale_price else None,
        "min_stock": p.min_stock,
        "stock_by_warehouse": stock_detail,
        "comentario": p.comentario,
    }
    if user_role == "ADMIN" and p.cost_price is not None:
        result["cost_price"] = f"{p.cost_price:.2f}"

    return json.dumps(result, ensure_ascii=False)


def _exec_check_inventory(db: Session, args: dict, _user_role: str) -> str:
    q = db.query(Inventory, Product, Warehouse).join(
        Product, Inventory.product_id == Product.id
    ).join(
        Warehouse, Inventory.warehouse_id == Warehouse.id
    ).filter(Product.is_active == True)  # noqa: E712

    product_name = args.get("product_name")
    if product_name:
        q = q.filter(Product.name.ilike(f"%{product_name}%"))

    warehouse_name = args.get("warehouse_name")
    if warehouse_name:
        q = q.filter(Warehouse.name.ilike(f"%{warehouse_name}%"))

    if args.get("low_stock_only"):
        q = q.filter(Inventory.quantity < Product.min_stock)

    rows = q.limit(20).all()
    results = [
        {
            "product": p.name,
            "product_code": p.code,
            "warehouse": w.name,
            "quantity": inv.quantity,
            "min_stock": p.min_stock,
            "is_low": inv.quantity < p.min_stock,
        }
        for inv, p, w in rows
    ]
    return json.dumps(results, ensure_ascii=False)


def _exec_search_clients(db: Session, args: dict, _user_role: str) -> str:
    query = args.get("query", "")
    limit = min(args.get("limit", 10), 20)

    clients = (
        db.query(Client)
        .filter(
            Client.is_active == True,  # noqa: E712
            (Client.business_name.ilike(f"%{query}%"))
            | (Client.doc_number.ilike(f"%{query}%")),
        )
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": c.id,
            "business_name": c.business_name,
            "doc_type": c.doc_type,
            "doc_number": c.doc_number,
            "phone": c.phone,
            "zona": c.zona,
        }
        for c in clients
    ]
    return json.dumps(results, ensure_ascii=False)


def _exec_get_client_details(db: Session, args: dict, _user_role: str) -> str:
    client_id = args.get("client_id")
    c = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()  # noqa: E712
    if not c:
        return json.dumps({"error": "Cliente no encontrado"})

    result = {
        "id": c.id,
        "business_name": c.business_name,
        "ref_comercial": c.ref_comercial,
        "doc_type": c.doc_type,
        "doc_number": c.doc_number,
        "address": c.address,
        "zona": c.zona,
        "phone": c.phone,
        "email": c.email,
        "credit_limit": f"{c.credit_limit:.2f}" if c.credit_limit else None,
        "credit_days": c.credit_days,
        "comentario": c.comentario,
    }
    return json.dumps(result, ensure_ascii=False)


def _exec_get_sales_summary(db: Session, args: dict, user_role: str) -> str:
    period = args.get("period", "month")
    now = datetime.now()

    q = db.query(
        sa_func.count(Sale.id).label("count"),
        sa_func.coalesce(sa_func.sum(Sale.total), 0).label("total_revenue"),
    ).filter(Sale.status != "ANULADA")

    if period == "today":
        q = q.filter(sa_func.date(Sale.created_at) == now.date())
    elif period == "week":
        q = q.filter(Sale.created_at >= now - timedelta(days=7))
    elif period == "month":
        q = q.filter(Sale.created_at >= now.replace(day=1))
    elif period == "year":
        q = q.filter(Sale.created_at >= now.replace(month=1, day=1))

    seller_name = args.get("seller_name")
    if seller_name:
        q = q.join(User, Sale.seller_id == User.id).filter(
            User.full_name.ilike(f"%{seller_name}%")
        )

    row = q.first()
    result = {
        "period": period,
        "sale_count": row.count if row else 0,
        "total_revenue": f"{row.total_revenue:.2f}" if row else "0.00",
    }

    if user_role == "ADMIN":
        # Add profit info
        profit_q = (
            db.query(
                sa_func.coalesce(
                    sa_func.sum(SaleItem.line_total - SaleItem.quantity * Product.cost_price), 0
                )
            )
            .join(Sale, SaleItem.sale_id == Sale.id)
            .join(Product, SaleItem.product_id == Product.id)
            .filter(Sale.status != "ANULADA", Product.cost_price.isnot(None))
        )
        if period == "today":
            profit_q = profit_q.filter(sa_func.date(Sale.created_at) == now.date())
        elif period == "week":
            profit_q = profit_q.filter(Sale.created_at >= now - timedelta(days=7))
        elif period == "month":
            profit_q = profit_q.filter(Sale.created_at >= now.replace(day=1))
        elif period == "year":
            profit_q = profit_q.filter(Sale.created_at >= now.replace(month=1, day=1))

        profit = profit_q.scalar() or 0
        result["estimated_profit"] = f"{profit:.2f}"

    return json.dumps(result, ensure_ascii=False)


def _exec_search_sales(db: Session, args: dict, _user_role: str) -> str:
    limit = min(args.get("limit", 10), 20)

    q = db.query(Sale).filter(Sale.status != "ANULADA")

    client_name = args.get("client_name")
    if client_name:
        q = q.join(Client, Sale.client_id == Client.id).filter(
            Client.business_name.ilike(f"%{client_name}%")
        )

    product_name = args.get("product_name")
    if product_name:
        q = q.join(SaleItem, Sale.id == SaleItem.sale_id).filter(
            SaleItem.product_name.ilike(f"%{product_name}%")
        )

    from_date = args.get("from_date")
    if from_date:
        q = q.filter(Sale.created_at >= from_date)

    to_date = args.get("to_date")
    if to_date:
        q = q.filter(Sale.created_at <= to_date + " 23:59:59")

    sales = q.order_by(Sale.created_at.desc()).limit(limit).all()

    results = []
    for s in sales:
        results.append({
            "id": s.id,
            "doc": f"{s.doc_type} {s.series}-{s.doc_number}",
            "client": s.client.business_name if s.client else None,
            "seller": s.seller.full_name if s.seller else None,
            "total": f"{s.total:.2f}",
            "status": s.status,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else None,
            "items_count": len(s.items) if s.items else 0,
        })
    return json.dumps(results, ensure_ascii=False)


TOOL_DISPATCH = {
    "search_products": _exec_search_products,
    "get_product_details": _exec_get_product_details,
    "check_inventory": _exec_check_inventory,
    "search_clients": _exec_search_clients,
    "get_client_details": _exec_get_client_details,
    "get_sales_summary": _exec_get_sales_summary,
    "search_sales": _exec_search_sales,
}


def chat_with_gemini(
    db: Session,
    user: User,
    message: str,
    history: list[dict],
) -> str:
    """Send a message to Gemini with function calling support."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return "Error: la librería google-genai no está instalada."

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return "Error: GEMINI_API_KEY no está configurada."

    role_instruction = (
        ADMIN_INSTRUCTION if user.role == "ADMIN" else VENTAS_INSTRUCTION
    )
    system_text = SYSTEM_PROMPT.format(role_instruction=role_instruction)

    client = genai.Client(api_key=api_key)

    # Build Gemini tool definitions
    tool_defs = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
            )
            for t in TOOL_DECLARATIONS
        ]
    )

    # Build conversation history
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

    # Add current user message
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    config = types.GenerateContentConfig(
        system_instruction=system_text,
        tools=[tool_defs],
        temperature=0.3,
    )

    # Function calling loop (max 5 iterations)
    for _ in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Error al comunicarse con el asistente: {str(e)}"

        # Check if model wants to call functions
        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            return response.text or "No pude generar una respuesta."

        has_function_call = any(
            part.function_call for part in candidate.content.parts if part.function_call
        )

        if not has_function_call:
            # Model returned final text
            return response.text or "No pude generar una respuesta."

        # Process function calls
        contents.append(candidate.content)

        function_response_parts = []
        for part in candidate.content.parts:
            if not part.function_call:
                continue

            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args) if part.function_call.args else {}

            logger.info(f"Gemini calling tool: {fn_name}({fn_args})")

            executor = TOOL_DISPATCH.get(fn_name)
            if executor:
                try:
                    result = executor(db, fn_args, user.role)
                except Exception as e:
                    logger.error(f"Tool execution error: {fn_name}: {e}")
                    result = json.dumps({"error": f"Error ejecutando {fn_name}: {str(e)}"})
            else:
                result = json.dumps({"error": f"Herramienta desconocida: {fn_name}"})

            function_response_parts.append(
                types.Part.from_function_response(
                    name=fn_name,
                    response={"result": result},
                )
            )

        contents.append(types.Content(role="user", parts=function_response_parts))

    return "Se alcanzó el límite de consultas internas. Por favor, reformula tu pregunta."
