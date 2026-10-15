from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import am, attachments, auth, matching, pm, system


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Sistema DVI Offline — CCDVI/SEPOL",
        version="0.1.0",
        description=(
            "API de apoio à identificação de vítimas de desastres (DVI), com referência metodológica "
            "no INTERPOL DVI Guide 2023. USO DEMONSTRATIVO COM DADOS FICTÍCIOS. Não é sistema "
            "homologado pela INTERPOL e não realiza identificação automática."
        ),
        # Swagger UI/ReDoc carregam recursos de CDN; desabilitados para operação sem internet.
        # O esquema OpenAPI continua disponível em /api/openapi.json.
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    if settings.dev_cors_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.dev_cors_origin],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    for r in (auth.router, am.router, pm.router, attachments.router, matching.router, system.router):
        app.include_router(r)
    return app


app = create_app()
