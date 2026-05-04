from fastapi import APIRouter
from src.api.v1.endpoints import b53

api_router = APIRouter()
api_router.include_router(b53.router, prefix="/b53", tags=["Costos B53 (PostgreSQL)"])
