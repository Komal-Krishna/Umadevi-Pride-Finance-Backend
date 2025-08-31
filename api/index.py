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

# Try to import and include routers - handle missing modules gracefully
try:
    from app.api.v1 import vehicles
    app.include_router(vehicles.router, prefix="/api/v1", tags=["Vehicles"])
    print("Vehicles router loaded successfully")
except ImportError as e:
    print(f"Could not load vehicles router: {e}")

try:
    from app.api.v1 import auth
    app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
    print("Auth router loaded successfully")
except ImportError as e:
    print(f"Could not load auth router: {e}")

try:
    from app.api.v1 import dashboard
    app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
    print("Dashboard router loaded successfully")
except ImportError as e:
    print(f"Could not load dashboard router: {e}")

try:
    from app.api.v1 import loans
    app.include_router(loans.router, prefix="/api/v1", tags=["Loans"])
    print("Loans router loaded successfully")
except ImportError as e:
    print(f"Could not load loans router: {e}")

try:
    from app.api.v1 import outside_interest
    app.include_router(outside_interest.router, prefix="/api/v1", tags=["Outside Interest"])
    print("Outside Interest router loaded successfully")
except ImportError as e:
    print(f"Could not load outside interest router: {e}")

try:
    from app.api.v1 import payments
    app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])
    print("Payments router loaded successfully")
except ImportError as e:
    print(f"Could not load payments router: {e}")

try:
    from app.api.v1 import analytics
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
    print("Analytics router loaded successfully")
except ImportError as e:
    print(f"Could not load analytics router: {e}")

@app.get("/")
async def root():
    return {"message": "Uma Devi's Pride Finance Management System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/debug")
async def debug_info():
    """Debug endpoint to see what's working"""
    return {
        "message": "Debug info",
        "python_path": sys.path,
        "current_dir": str(current_dir),
        "project_root": str(project_root),
        "available_modules": [m for m in sys.modules.keys() if m.startswith('app')]
    }

# Export for Vercel
handler = app
