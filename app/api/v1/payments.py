from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.base import PaymentCreate, PaymentUpdate, PaymentResponse, VehiclePaymentCreate
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/", response_model=List[PaymentResponse])
async def get_payments(
    vehicle_id: Optional[int] = None,
    source_type: Optional[str] = None,
    source_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all payments with optional filters"""
    try:
        # If vehicle_id is provided, use it as source_id with source_type as 'vehicle'
        if vehicle_id:
            payments = await db.get_payments("vehicle", vehicle_id)
        else:
            payments = await db.get_payments(source_type, source_id)
        return payments
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payments"
        )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get a specific payment by ID"""
    try:
        payments = await db.get_payments()
        payment = next((p for p in payments if p["id"] == payment_id), None)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        return payment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payment"
        )

@router.post("/", response_model=PaymentResponse)
@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment: VehiclePaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new payment record"""
    try:
        # Convert VehiclePaymentCreate to the format expected by the database
        payment_data = {
            "source_type": "vehicle",
            "source_id": payment.vehicle_id,
            "amount": payment.amount,
            "payment_date": payment.payment_date.isoformat() if hasattr(payment.payment_date, 'isoformat') else str(payment.payment_date),
            "payment_type": "credit",  # All vehicle payments are credits (money received)
            "description": payment.notes or "",  # Handle None values
            "payment_status": "PAID"
        }
        
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
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating payment"
        )

@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Update an existing payment record"""
    try:
        # Check if payment exists
        payments = await db.get_payments()
        existing_payment = next((p for p in payments if p["id"] == payment_id), None)
        
        if not existing_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Update payment
        update_data = {k: v for k, v in payment_update.dict().items() if v is not None}
        
        # For now, we'll use a simple approach since we don't have update_payment method
        # In a real implementation, you'd add this method to DatabaseManager
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment update not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating payment"
        )

@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Delete a payment record"""
    try:
        # Check if payment exists
        payments = await db.get_payments()
        existing_payment = next((p for p in payments if p["id"] == payment_id), None)
        
        if not existing_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # For now, we'll use a simple approach since we don't have delete_payment method
        # In a real implementation, you'd add this method to DatabaseManager
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment deletion not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting payment"
        )
