from fastapi import APIRouter, HTTPException, status, Depends
from app.models.base import DashboardSummary, FinanceOverview
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get dashboard summary with counts and totals"""
    try:
        # Get all data
        vehicles = await db.get_vehicles()
        outside_interests = await db.get_outside_interest()
        payments = await db.get_payments()
        
        # Calculate summary
        total_vehicles = len(vehicles)
        active_vehicles = len([v for v in vehicles if not v["is_closed"]])
        closed_vehicles = len([v for v in vehicles if v["is_closed"]])
        
        total_outside_interest = len(outside_interests)
        active_outside_interest = len([i for i in outside_interests if not i["is_closed"]])
        closed_outside_interest = len([i for i in outside_interests if i["is_closed"]])
        
        # Calculate payment totals for current month
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        total_payments_this_month = sum(
            p["amount"] for p in payments 
            if p["payment_type"] == "credit" 
            and datetime.fromisoformat(p["payment_date"].replace('T', ' ')).month == current_month
            and datetime.fromisoformat(p["payment_date"].replace('T', ' ')).year == current_year
        )
        
        pending_payments = sum(
            p["amount"] for p in payments 
            if p["payment_type"] == "debit" 
            and p["payment_status"] == "PENDING"
        )
        
        # Calculate total principle amount
        total_principle_amount = sum(
            v["principle_amount"] for v in vehicles if not v["is_closed"]
        ) + sum(
            i["principle_amount"] for i in outside_interests if not i["is_closed"]
        )
        
        return DashboardSummary(
            total_vehicles=total_vehicles,
            active_vehicles=active_vehicles,
            closed_vehicles=closed_vehicles,
            total_outside_interest=total_outside_interest,
            active_outside_interest=active_outside_interest,
            closed_outside_interest=closed_outside_interest,
            total_payments_this_month=total_payments_this_month,
            pending_payments=pending_payments,
            total_principle_amount=total_principle_amount
        )
        
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching dashboard summary"
        )

@router.get("/overview", response_model=FinanceOverview)
async def get_finance_overview(
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get comprehensive finance overview with all data"""
    try:
        # Get all data
        vehicles = await db.get_vehicles()
        outside_interests = await db.get_outside_interest()
        payments = await db.get_payments()
        
        # Get recent payments (last 10)
        recent_payments = sorted(
            payments, 
            key=lambda x: x["created_at"], 
            reverse=True
        )[:10]
        
        # Get dashboard summary
        summary = await get_dashboard_summary(current_user, db)
        
        return FinanceOverview(
            vehicles=vehicles,
            outside_interests=outside_interests,
            recent_payments=recent_payments,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error fetching finance overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching finance overview"
        )
