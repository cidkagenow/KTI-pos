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
from app.services.system_knowledge import build_knowledge_base

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Eres el asistente virtual de KTI POS, un sistema de punto de venta para repuestos automotrices. \
Tu rol es ayudar a los trabajadores respondiendo sus preguntas.

{knowledge_base}

REGLAS:

1. Para preguntas sobre repuestos/piezas (ej: "carburador para la ZL", "filtro de aceite toyota yaris", "pastillas de freno CBR"):
   - SIEMPRE usa web_search PRIMERO para encontrar información técnica y compatibilidad.
   - Responde con la información encontrada en la web.
   - Luego PREGUNTA: "¿Quieres que revise si lo tenemos en inventario?"
   - Solo busca en el inventario si el usuario dice que sí.

2. Para consultas EXPLÍCITAS sobre inventario, precios o stock — SOLO cuando usen palabras como "tienes", "cuánto", "precio", "costo", "stock":
   - Usa search_products o check_inventory INMEDIATAMENTE.
   - Si no encuentras, prueba con palabras diferentes (solo marca, solo categoría, etc.)

3. Para preguntas generales (especificaciones, "qué X usa el Y", etc.):
   - Usa web_search INMEDIATAMENTE. NO busques en el inventario.

4. Para consultas sobre datos del POS (ventas, clientes, reportes):
   - Usa las herramientas de base de datos INMEDIATAMENTE.

5. Para saludos simples (hola, buenos días), responde amablemente sin usar herramientas.
6. SIEMPRE responde en español. Usa S/ para los montos (Soles peruanos).
7. NUNCA inventes datos. NUNCA pidas permiso para buscar — SIEMPRE actúa directamente.
8. {role_instruction}

MENSAJES INCOMPLETOS O ABREVIADOS:
Los trabajadores suelen escribir mensajes cortos, abreviados o con errores tipográficos.
- NUNCA les pidas que reformulen la pregunta. INTERPRETA lo mejor que puedas y ACTÚA.
- Por defecto, trata CADA mensaje sobre repuestos/piezas como una búsqueda web (regla 1).
- SOLO busca en el inventario cuando el usuario use palabras como: "tienes", "cuánto", "precio", "costo", "stock", "busca en el sistema", "sí" (confirmando búsqueda).
- Ejemplos de cómo interpretar:
  - "carburador para la zll" → web_search "carburador compatible Honda ZL" (typo: zll=ZL)
  - "pastillas cbr" → web_search "pastillas de freno Honda CBR"
  - "filtro aceite toyota yaris" → web_search "filtro de aceite compatible Toyota Yaris"
  - "filtro acete" → web_search "filtro de aceite repuesto" (búsqueda web por defecto)
  - "kit arrastre cgl" → web_search "kit de arrastre Honda CGL"
  - "llanta 90 90 18" → web_search "llanta 90/90-18 motocicleta"
  - "¿cuánto está el filtro?" → search_products "filtro" (pregunta EXPLÍCITA de precio → inventario)
  - "¿tienes aceite?" → search_products "aceite" (pregunta EXPLÍCITA de stock → inventario)
  - "¿hay para honda?" → search_products brand="honda" (pregunta EXPLÍCITA de stock → inventario)
  - "sí, busca en inventario" → search_products (usuario confirmó)
- Las letras dobles suelen ser errores: "zll"="zl", "cbrr"="cbr", "hondaa"="honda"
- Abreviaturas comunes en español que pueden escribir: "d"="de", "q"="que", "pa"="para", "x"="por", "tb"="también"
- Modelos de motos comunes en Perú: ZL, CGL, XL, CBR, CRF, GL, NXR, XR, Wave, Biz, PCX, Navi

CONSEJOS PARA BUSCAR EN INVENTARIO:
- Los usuarios preguntan por nombres coloquiales: "llanta duro" → "duro" es la MARCA, "llanta" es el tipo
- Si no encuentras, prueba: solo la categoría (ej: "filtro de aceite"), solo la marca, o palabras individuales
- search_products busca en nombre, código Y marca
- Haz al menos 2 búsquedas diferentes si la primera no devuelve resultados
- Formatea los resultados como una lista con código, nombre, marca, precio y stock
"""

VENTAS_INSTRUCTION = (
    "El usuario tiene el rol VENTAS: NO puede ver precios de costo ni utilidad/margen. "
    "Si pregunta sobre costos o utilidades, dile que no tiene permiso."
)
ADMIN_INSTRUCTION = (
    "El usuario tiene el rol ADMIN: puede ver toda la información incluyendo costos y utilidades."
)

# Tool declarations for Gemini function calling
TOOL_DECLARATIONS = [
    {
        "name": "web_search",
        "description": "Search the internet using Google. Use for general questions that are NOT about POS system data. Examples: technical specs of motorcycles/cars, spare parts compatibility, part dimensions, market product information, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to search on Google (in English or Spanish, whichever fits best)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_products",
        "description": "Search products by name, code or brand. Returns a list with prices and stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search in product name or code",
                },
                "brand": {
                    "type": "string",
                    "description": "Filter by brand name (partial match)",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category name (partial match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                },
            },
        },
    },
    {
        "name": "get_product_details",
        "description": "Get detailed information for a product by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "Product ID",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Check stock levels. Can filter by product, warehouse, or only low stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Filter by product name (partial match)",
                },
                "warehouse_name": {
                    "type": "string",
                    "description": "Filter by warehouse name",
                },
                "low_stock_only": {
                    "type": "boolean",
                    "description": "If true, only show products with stock below minimum",
                },
            },
        },
    },
    {
        "name": "search_clients",
        "description": "Search clients by name or document number (RUC/DNI).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search in name or document number",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_client_details",
        "description": "Get detailed information for a client by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "integer",
                    "description": "Client ID",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "get_sales_summary",
        "description": "Get sales summary: count, total revenue. Can filter by period and seller.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Period: 'today', 'week', 'month', 'year', or 'all' (default 'month')",
                },
                "seller_name": {
                    "type": "string",
                    "description": "Filter by seller name",
                },
            },
        },
    },
    {
        "name": "search_sales",
        "description": "Search recent sales. Can filter by client, product, or date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {
                    "type": "string",
                    "description": "Filter by client name",
                },
                "product_name": {
                    "type": "string",
                    "description": "Filter by product name in items",
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                },
                "to_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
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


def _exec_web_search(_db: Session, args: dict, _user_role: str) -> str:
    """Execute a Google Search via a separate Gemini call with grounding."""
    query = args.get("query", "")
    if not query:
        return json.dumps({"error": "No se proporcionó consulta"})

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        search_tool = types.Tool(google_search=types.GoogleSearch())

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[search_tool],
                temperature=0.3,
            ),
        )
        return response.text or "No se encontraron resultados."
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return json.dumps({"error": f"Error en búsqueda web: {str(e)}"})


TOOL_DISPATCH = {
    "web_search": _exec_web_search,
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
    knowledge_base = build_knowledge_base(user.role)
    system_text = SYSTEM_PROMPT.format(
        knowledge_base=knowledge_base,
        role_instruction=role_instruction,
    )

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
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        ),
        temperature=0.5,
    )

    # Helper to safely extract text
    def _safe_text(resp) -> str:
        try:
            return resp.text or ""
        except Exception:
            return ""

    # Function calling loop (max 5 iterations)
    for iteration in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Error al comunicarse con el asistente: {str(e)}"

        # Check if model wants to call functions
        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            logger.warning(f"Gemini empty response (iter {iteration}). candidates={response.candidates}")
            if candidate and hasattr(candidate, 'finish_reason'):
                logger.warning(f"Finish reason: {candidate.finish_reason}")
            text = _safe_text(response)
            return text or "Lo siento, no pude procesar tu consulta. Por favor intenta de nuevo."

        has_function_call = any(
            part.function_call for part in candidate.content.parts if part.function_call
        )

        if not has_function_call:
            # Model returned final text
            text = _safe_text(response)
            logger.info(f"Gemini final text (iter {iteration}): {text[:200]}")
            return text or "Lo siento, no pude procesar tu consulta. Por favor intenta de nuevo."

        # Process function calls
        contents.append(candidate.content)

        function_response_parts = []
        for part in candidate.content.parts:
            if not part.function_call:
                continue

            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args) if part.function_call.args else {}

            logger.warning(f"Gemini calling tool: {fn_name}({fn_args})")

            executor = TOOL_DISPATCH.get(fn_name)
            if executor:
                try:
                    result = executor(db, fn_args, user.role)
                    logger.warning(f"Tool {fn_name} result: {result[:300] if result else 'empty'}")
                except Exception as e:
                    logger.error(f"Tool execution error: {fn_name}: {e}", exc_info=True)
                    result = json.dumps({"error": f"Error executing {fn_name}: {str(e)}"})
            else:
                result = json.dumps({"error": f"Unknown tool: {fn_name}"})

            function_response_parts.append(
                types.Part.from_function_response(
                    name=fn_name,
                    response={"result": result},
                )
            )

        contents.append(types.Content(role="user", parts=function_response_parts))

    return "Se alcanzó el límite interno de consultas. Por favor reformula tu pregunta."
