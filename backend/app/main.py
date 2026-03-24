from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, users, clients, products, catalogs, sales, inventory, purchases, reports, peru_consult, sunat, chat, trabajadores, online_orders, accounts_payable
from app.config import settings
from app.scheduler import init_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="KTI POS", version="0.1.0", redirect_slashes=False, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(catalogs.router, prefix="/api/v1/catalogs", tags=["catalogs"])
app.include_router(sales.router, prefix="/api/v1/sales", tags=["sales"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])
app.include_router(purchases.router, prefix="/api/v1/purchase-orders", tags=["purchases"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(peru_consult.router, prefix="/api/v1/lookup", tags=["lookup"])
app.include_router(sunat.router, prefix="/api/v1/sunat", tags=["sunat"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(trabajadores.router, prefix="/api/v1/trabajadores", tags=["trabajadores"])
app.include_router(online_orders.router, prefix="/api/v1/online-orders", tags=["online-orders"])
app.include_router(accounts_payable.router, prefix="/api/v1/accounts-payable", tags=["accounts-payable"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
