from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.v1.api import api_router

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# Configuración CORS para que "www.gestionpose.com.ar" pueda consumir la API
origins = [
    "http://localhost",
    "http://localhost:3000",  # Frontend en local
    "http://www.gestionpose.com.ar",
    "https://www.gestionpose.com.ar",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": "Welcome to Pose API"}


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
