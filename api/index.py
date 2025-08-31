import sys
import os
from pathlib import Path

# Get the current file's directory and add parent to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Import FastAPI and create app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our modules
from app.api.v1 import vehicles, auth, dashboard, loans, outside_interest, payments, analytics
from app.core.auth import AuthManager
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="Uma Devi's Pride Finance Management System",
    description="Backend API for managing vehicles, loans, and financial records",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(vehicles.router, prefix="/api/v1", tags=["Vehicles"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(loans.router, prefix="/api/v1", tags=["Loans"])
app.include_router(outside_interest.router, prefix="/api/v1", tags=["Outside Interest"])
app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])

@app.get("/")
async def root():
    return {"message": "Uma Devi's Pride Finance Management System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Export for Vercel
handler = app
