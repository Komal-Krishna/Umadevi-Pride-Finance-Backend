from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1 import auth, vehicles, outside_interest, payments, dashboard, loans, analytics
from app.database.connection import get_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper connection handling"""
    # Startup
    db = get_db()  # Initialize singleton
    
    yield
    
    # Shutdown
    await db.close()

app = FastAPI(title="Uma Devi's Pride Finance API", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(outside_interest.router, prefix="/api/v1")
app.include_router(loans.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Uma Devi's Pride Finance API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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
