from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.v1 import auth, vehicles, outside_interest, payments, dashboard, loans
from app.database.connection import get_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Uma Devi's Pride Finance API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("Starting up Uma Devi's Pride Finance API")
    # Initialize database connection
    db = get_db()
    logger.info("Database connection initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on shutdown"""
    logger.info("Shutting down Uma Devi's Pride Finance API")
    # Clean up database connection using the proper close function
    from app.database.connection import close_db
    await close_db()
    logger.info("Database connection closed")

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(outside_interest.router, prefix="/api/v1")
app.include_router(loans.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Uma Devi's Pride Finance API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health/db")
async def database_health_check():
    """Check database connection health"""
    try:
        db = get_db()
        is_healthy = await db.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "connected" if is_healthy else "disconnected"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
