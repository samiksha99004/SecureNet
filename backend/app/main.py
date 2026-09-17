"""
SecureNet Backend — Main Application

FastAPI application entry point with CORS, exception handling,
and route registration.
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
import json

from app.core.config import settings
from app.utils.logger import logger

# Import routes
from app.api.routes import auth, events, dashboard, settings_routes, model, reports, health, ids

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Network-Based Behavioural Intrusion Detection System",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    # Serialize response models using field aliases (camelCase)
    response_model_by_alias=True,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware to ensure response models use aliases (camelCase)
class ResponseAliasMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response


app.add_middleware(ResponseAliasMiddleware)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        if field not in errors:
            errors[field] = []
        errors[field].append(error["msg"])
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": 422,
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": errors
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": 500,
            "code": "DATABASE_ERROR",
            "message": "A database error occurred"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": 500,
            "code": "INTERNAL_ERROR",
            "message": "An internal server error occurred" if not settings.DEBUG else str(exc)
        }
    )


# Register routes with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(model.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(ids.router, prefix="/api")
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize ML models (Ensemble version)
    logger.info("Initializing ML models (Ensemble: Random Forest + XGBoost)...")
    from app.ml.models_ensemble import initialize_ml_models
    ml_loaded = initialize_ml_models()
    if ml_loaded:
        logger.info("✓ ML models loaded successfully (Ensemble)")
    else:
        logger.warning("⚠ ML models failed to load - IDS functionality will be limited")
    
    # Initialize IDS service (Ensemble version)
    logger.info("Initializing IDS service (Ensemble)...")
    from app.ml.ids_service_ensemble import initialize_ids
    ids_ready = await initialize_ids()
    if ids_ready:
        logger.info("✓ IDS service initialized (Ensemble)")
    else:
        logger.warning("⚠ IDS service initialization failed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info(f"{settings.APP_NAME} shutting down...")


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint for real-time security event streaming"""
    from app.websocket.manager import manager
    
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive pings/messages
            data = await websocket.receive_text()
            # Echo or ignore - manager broadcasts events from IDS
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }
