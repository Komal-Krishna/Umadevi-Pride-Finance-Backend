from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.base import ChitCreate, ChitUpdate, ChitResponse, ChitCollect
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chits", tags=["Chits"])

@router.get("/", response_model=List[ChitResponse])
async def get_chits(
    is_closed: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all chits with profit calculations"""
    try:
        chits = await db.get_chits(is_closed)
        
        # Calculate profit for each chit
        for chit in chits:
            # Get payments for this chit
            payments = await db.get_payments("chit", chit["id"])
            
            # Calculate totals
            total_payments = sum(payment["amount"] for payment in payments)
            expected_total = chit["monthly_amount"] * len(payments) if payments else 0
            total_profit = expected_total - total_payments if expected_total > 0 else 0
            profit_percentage = (total_profit / chit["total_amount"]) * 100 if chit["total_amount"] > 0 else 0
            
            # Calculate collected analysis (only if chit is collected)
            collected_amount = chit.get("collected_amount", 0) or 0
            net_profit = collected_amount - total_payments if chit.get("is_collected", False) else 0
            net_profit_percentage = (net_profit / total_payments) * 100 if total_payments > 0 and chit.get("is_collected", False) else 0
            
            # Add calculated fields
            chit["total_payments"] = total_payments
            chit["total_profit"] = total_profit
            chit["profit_percentage"] = profit_percentage
            chit["payments_count"] = len(payments)
            chit["collected_amount"] = collected_amount
            chit["net_profit"] = net_profit
            chit["net_profit_percentage"] = net_profit_percentage
        
        return chits
    except Exception as e:
        logger.error(f"Error fetching chits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching chits"
        )

@router.get("/{chit_id}", response_model=ChitResponse)
async def get_chit(
    chit_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get a specific chit with profit calculations"""
    try:
        chit = await db.get_chit_by_id(chit_id)
        
        if not chit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit not found"
            )
        
        # Get payments for this chit
        payments = await db.get_payments("chit", chit_id)
        
        # Calculate totals
        total_payments = sum(payment["amount"] for payment in payments)
        expected_total = chit["monthly_amount"] * len(payments) if payments else 0
        total_profit = expected_total - total_payments if expected_total > 0 else 0
        profit_percentage = (total_profit / chit["total_amount"]) * 100 if chit["total_amount"] > 0 else 0
        
        # Calculate collected analysis (only if chit is collected)
        collected_amount = chit.get("collected_amount", 0) or 0
        net_profit = collected_amount - total_payments if chit.get("is_collected", False) else 0
        net_profit_percentage = (net_profit / total_payments) * 100 if total_payments > 0 and chit.get("is_collected", False) else 0
        
        # Add calculated fields
        chit["total_payments"] = total_payments
        chit["total_profit"] = total_profit
        chit["profit_percentage"] = profit_percentage
        chit["payments_count"] = len(payments)
        chit["collected_amount"] = collected_amount
        chit["net_profit"] = net_profit
        chit["net_profit_percentage"] = net_profit_percentage
        
        return chit
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching chit"
        )

@router.post("/", response_model=ChitResponse)
async def create_chit(
    chit: ChitCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new chit"""
    try:
        # Calculate monthly amount
        monthly_amount = chit.total_amount / chit.duration_months
        
        chit_data = {
            "chit_name": chit.chit_name,
            "total_amount": chit.total_amount,
            "duration_months": chit.duration_months,
            "monthly_amount": monthly_amount,
            "to_whom": chit.to_whom,
            "start_date": chit.start_date.isoformat() if hasattr(chit.start_date, 'isoformat') else str(chit.start_date),
            "is_closed": False
        }
        
        created_chit = await db.create_chit(chit_data)
        
        if not created_chit:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating chit"
            )
        
        # Add default calculated fields for new chit
        created_chit["total_payments"] = 0.0
        created_chit["total_profit"] = 0.0
        created_chit["profit_percentage"] = 0.0
        
        return created_chit
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating chit"
        )

@router.put("/{chit_id}", response_model=ChitResponse)
async def update_chit(
    chit_id: int,
    chit_update: ChitUpdate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Update an existing chit"""
    try:
        # Check if chit exists
        existing_chit = await db.get_chit_by_id(chit_id)
        
        if not existing_chit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit not found"
            )
        
        # Prepare update data
        update_data = {k: v for k, v in chit_update.dict().items() if v is not None}
        
        # Recalculate monthly amount if total_amount or duration_months changed
        if "total_amount" in update_data or "duration_months" in update_data:
            total_amount = update_data.get("total_amount", existing_chit["total_amount"])
            duration_months = update_data.get("duration_months", existing_chit["duration_months"])
            update_data["monthly_amount"] = total_amount / duration_months
        
        updated_chit = await db.update_chit(chit_id, update_data)
        
        if not updated_chit:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating chit"
            )
        
        # Calculate profit for updated chit
        payments = await db.get_payments("chit", chit_id)
        total_payments = sum(payment["amount"] for payment in payments)
        expected_total = updated_chit["monthly_amount"] * len(payments) if payments else 0
        total_profit = expected_total - total_payments if expected_total > 0 else 0
        profit_percentage = (total_profit / updated_chit["total_amount"]) * 100 if updated_chit["total_amount"] > 0 else 0
        
        updated_chit["total_payments"] = total_payments
        updated_chit["total_profit"] = total_profit
        updated_chit["profit_percentage"] = profit_percentage
        
        return updated_chit
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating chit"
        )

@router.post("/{chit_id}/close")
async def close_chit(
    chit_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Close a chit"""
    try:
        success = await db.close_chit(chit_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit not found or already closed"
            )
        
        return {"message": "Chit closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing chit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing chit"
        )

@router.post("/{chit_id}/collect")
async def collect_chit(
    chit_id: int,
    collect_data: ChitCollect,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Mark a chit as collected"""
    try:
        # Check if chit exists
        existing_chit = await db.get_chit_by_id(chit_id)
        
        if not existing_chit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit not found"
            )
        
        # Check if chit is already collected
        if existing_chit.get("is_collected", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chit is already collected"
            )
        
        success = await db.collect_chit(
            chit_id, 
            collect_data.collected_amount, 
            collect_data.collected_date.isoformat()
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to collect chit"
            )
        
        return {"message": "Chit collected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting chit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error collecting chit"
        )

@router.delete("/{chit_id}")
async def delete_chit(
    chit_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Delete a chit"""
    try:
        success = await db.delete_chit(chit_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit not found"
            )
        
        return {"message": "Chit deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting chit"
        )

@router.get("/{chit_id}/payments")
async def get_chit_payments(
    chit_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all payments for a specific chit with profit calculations"""
    try:
        # Get chit details
        chit = await db.get_chit_by_id(chit_id)
        
        if not chit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit not found"
            )
        
        # Get payments
        payments = await db.get_payments("chit", chit_id)
        
        # Calculate profit for each payment
        for payment in payments:
            expected_amount = chit["monthly_amount"]
            actual_amount = payment["amount"]
            profit = expected_amount - actual_amount
            profit_percentage = (profit / expected_amount) * 100 if expected_amount > 0 else 0
            
            payment["expected_amount"] = expected_amount
            payment["profit"] = profit
            payment["profit_percentage"] = profit_percentage
        
        return {
            "chit": chit,
            "payments": payments,
            "total_payments": len(payments),
            "total_amount_received": sum(p["amount"] for p in payments),
            "total_expected": chit["monthly_amount"] * len(payments) if payments else 0,
            "total_profit": sum(p["profit"] for p in payments),
            "overall_profit_percentage": (sum(p["profit"] for p in payments) / chit["total_amount"]) * 100 if chit["total_amount"] > 0 else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chit payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching chit payments"
        )
