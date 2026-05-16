from fastapi import APIRouter
from src.api.v1.endpoints import b53

api_router = APIRouter()
api_router.include_router(
    b53.router,
    prefix="/b52",
    tags=["Costos B52 (PostgreSQL)"],
)
# Compatibilidad temporal con clientes que aún consumen /b53.
api_router.include_router(
    b53.router,
    prefix="/b53",
    tags=["Costos B52 (compatibilidad /b53)"],
)
