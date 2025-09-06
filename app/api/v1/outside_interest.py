from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.base import (
    OutsideInterestCreate, OutsideInterestUpdate, OutsideInterestResponse,
    PaymentCreate, PaymentResponse
)
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outside_interest", tags=["Outside Interest"])

@router.get("/", response_model=List[OutsideInterestResponse])
async def get_outside_interests(
    is_closed: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all outside interest records with optional closed status filter"""
    try:
        interests = await db.get_outside_interest(is_closed)
        
        # Calculate extended days and payment totals for each interest record
        for interest in interests:
            interest["extended_days"] = await calculate_extended_days(interest)
            interest["total_payments"], interest["pending_amount"] = await calculate_payment_totals(
                db, "outside_interest", interest["id"]
            )
        
        return interests
    except Exception as e:
        logger.error(f"Error fetching outside interests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching outside interests"
        )

@router.get("/{interest_id}", response_model=OutsideInterestResponse)
async def get_outside_interest(
    interest_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get a specific outside interest record by ID"""
    try:
        interests = await db.get_outside_interest()
        interest = next((i for i in interests if i["id"] == interest_id), None)
        
        if not interest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outside interest record not found"
            )
        
        # Calculate extended days and payment totals
        interest["extended_days"] = await calculate_extended_days(interest)
        interest["total_payments"], interest["pending_amount"] = await calculate_payment_totals(
            db, "outside_interest", interest_id
        )
        
        return interest
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching outside interest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching outside interest"
        )

@router.post("/", response_model=OutsideInterestResponse)
async def create_outside_interest(
    interest: OutsideInterestCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new outside interest record"""
    try:
        interest_data = interest.dict()
        interest_data["is_closed"] = False
        interest_data["created_at"] = datetime.utcnow()
        
        created_interest = await db.create_outside_interest(interest_data)
        
        if not created_interest:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating outside interest record"
            )
        
        return created_interest
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating outside interest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating outside interest record"
        )

@router.put("/{interest_id}", response_model=OutsideInterestResponse)
async def update_outside_interest(
    interest_id: int,
    interest_update: OutsideInterestUpdate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Update an existing outside interest record"""
    try:
        # Check if interest record exists
        interests = await db.get_outside_interest()
        existing_interest = next((i for i in interests if i["id"] == interest_id), None)
        
        if not existing_interest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outside interest record not found"
            )
        
        # Update interest record
        update_data = {k: v for k, v in interest_update.dict().items() if v is not None}
        updated_interest = await db.update_outside_interest(interest_id, update_data)
        
        if not updated_interest:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating outside interest record"
            )
        
        return updated_interest
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating outside interest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating outside interest record"
        )

@router.post("/{interest_id}/close")
async def close_outside_interest(
    interest_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Close an outside interest record"""
    try:
        success = await db.close_outside_interest(interest_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error closing outside interest record"
            )
        
        return {"message": "Outside interest record closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing outside interest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing outside interest record"
        )

@router.post("/{interest_id}/payments", response_model=PaymentResponse)
async def create_payment(
    interest_id: int,
    payment: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a payment record for an outside interest"""
    try:
        payment_data = payment.dict()
        payment_data["source_type"] = "outside_interest"
        payment_data["source_id"] = interest_id
        payment_data["payment_status"] = "PAID"
        payment_data["created_at"] = datetime.utcnow()
        
        created_payment = await db.create_payment(payment_data)
        
        if not created_payment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating payment"
            )
        
        return created_payment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating interest payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating payment"
        )

@router.get("/{interest_id}/payments", response_model=List[PaymentResponse])
async def get_payments(
    interest_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all payments for a specific outside interest record"""
    try:
        # Check if interest record exists
        interests = await db.get_outside_interest()
        existing_interest = next((i for i in interests if i["id"] == interest_id), None)
        
        if not existing_interest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outside interest record not found"
            )
        
        # Get payments for this interest record
        payments = await db.get_payments("outside_interest", interest_id)
        
        return payments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching outside interest payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payments"
        )

async def calculate_extended_days(interest: dict) -> Optional[int]:
    """Calculate extended days beyond exact months"""
    try:
        if interest["is_closed"]:
            return None
        
        lending_date = interest["date_of_lending"]
        if isinstance(lending_date, str):
            lending_date = datetime.strptime(lending_date, "%Y-%m-%d").date()
        
        today = date.today()
        
        # Calculate months difference
        months_diff = (today.year - lending_date.year) * 12 + (today.month - lending_date.month)
        
        # Calculate expected end date based on payment frequency
        if interest["payment_frequency"] == "monthly":
            expected_months = months_diff
        elif interest["payment_frequency"] == "bimonthly":
            expected_months = months_diff * 2
        elif interest["payment_frequency"] == "quarterly":
            expected_months = months_diff * 3
        
        # Calculate expected end date
        expected_end_date = lending_date.replace(day=1)
        for _ in range(expected_months):
            if expected_end_date.month == 12:
                expected_end_date = expected_end_date.replace(year=expected_end_date.year + 1, month=1)
            else:
                expected_end_date = expected_end_date.replace(month=expected_end_date.month + 1)
        
        # Calculate extended days
        if today > expected_end_date:
            return (today - expected_end_date).days
        
        return 0
    except Exception as e:
        logger.error(f"Error calculating extended days: {e}")
        return None

async def calculate_payment_totals(db: DatabaseManager, source_type: str, source_id: int) -> tuple[float, float]:
    """Calculate total payments and pending amount for a source"""
    try:
        payments = await db.get_payments(source_type, source_id)
        
        total_payments = sum(p["amount"] for p in payments if p["payment_type"] == "credit")
        pending_amount = sum(p["amount"] for p in payments if p["payment_type"] == "debit")
        
        return total_payments, pending_amount
    except Exception as e:
        logger.error(f"Error calculating payment totals: {e}")
        return 0.0, 0.0

@router.delete("/{interest_id}")
async def delete_outside_interest(
    interest_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Delete an outside interest record"""
    try:
        # Check if interest record exists
        interests = await db.get_outside_interest()
        existing_interest = next((i for i in interests if i["id"] == interest_id), None)
        
        if not existing_interest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outside interest record not found"
            )
        
        # Delete interest record
        success = await db.delete_outside_interest(interest_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting outside interest record"
            )
        
        return {"message": "Outside interest record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting outside interest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting outside interest record"
        )
