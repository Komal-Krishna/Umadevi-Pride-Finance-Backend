from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.base import PaymentCreate, PaymentUpdate, PaymentResponse, VehiclePaymentCreate
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/", response_model=List[dict])
async def get_payments(
    vehicle_id: Optional[int] = None,
    source_type: Optional[str] = None,
    source_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all payments with enhanced information from related tables"""
    try:
        # Get base payments
        if vehicle_id:
            payments = await db.get_payments("vehicle", vehicle_id)
        else:
            payments = await db.get_payments(source_type, source_id)
        
        # Get related data for all source types
        vehicles = await db.get_vehicles()
        loans = await db.get_loans()
        outside_interests = await db.get_outside_interest()
        chits = await db.get_chits()
        
        # Create lookup dictionaries
        vehicle_lookup = {v["id"]: v for v in vehicles}
        loan_lookup = {l["id"]: l for l in loans}
        outside_interest_lookup = {oi["id"]: oi for oi in outside_interests}
        chit_lookup = {c["id"]: c for c in chits}
        
        # Enhance payments with related information and filter out invalid ones
        enhanced_payments = []
        for payment in payments:
            enhanced_payment = payment.copy()
            valid_payment = False
            
            # Add source information based on source_type and source_id
            if payment["source_type"] == "vehicle" and payment.get("source_id"):
                vehicle = vehicle_lookup.get(payment["source_id"])
                if vehicle:
                    enhanced_payment["source_name"] = vehicle["vehicle_name"]
                    enhanced_payment["source_detail"] = f"Lent to: {vehicle['lend_to']}"
                    valid_payment = True
                # Skip payments with invalid vehicle IDs
            
            elif payment["source_type"] == "loan" and payment.get("source_id"):
                loan = loan_lookup.get(payment["source_id"])
                if loan:
                    enhanced_payment["source_name"] = loan["lender_name"]
                    enhanced_payment["source_detail"] = f"Type: {loan['lender_type']}"
                    valid_payment = True
                # Skip payments with invalid loan IDs
            
            elif payment["source_type"] == "outside_interest" and payment.get("source_id"):
                outside_interest = outside_interest_lookup.get(payment["source_id"])
                if outside_interest:
                    enhanced_payment["source_name"] = outside_interest["to_whom"]
                    enhanced_payment["source_detail"] = f"Category: {outside_interest['category']}"
                    valid_payment = True
                # Skip payments with invalid outside_interest IDs
            
            elif payment["source_type"] == "chit" and payment.get("source_id"):
                chit = chit_lookup.get(payment["source_id"])
                if chit:
                    enhanced_payment["source_name"] = chit["chit_name"]
                    enhanced_payment["source_detail"] = f"To: {chit['to_whom']}"
                    # Add profit calculations for chit payments
                    expected_amount = chit["monthly_amount"]
                    actual_amount = payment["amount"]
                    profit = expected_amount - actual_amount
                    profit_percentage = (profit / expected_amount) * 100 if expected_amount > 0 else 0
                    enhanced_payment["expected_amount"] = expected_amount
                    enhanced_payment["profit"] = profit
                    enhanced_payment["profit_percentage"] = profit_percentage
                    valid_payment = True
                # Skip payments with invalid chit IDs
            
            else:
                # For other source types or payments without source_id, include them
                enhanced_payment["source_name"] = payment["source_type"].title()
                enhanced_payment["source_detail"] = "Other"
                valid_payment = True
            
            # Only add valid payments to the result
            if valid_payment:
                enhanced_payments.append(enhanced_payment)
        
        return enhanced_payments
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
async def create_payment(
    payment: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new payment record"""
    try:
        # Convert PaymentCreate to the format expected by the database
        payment_data = {
            "source_type": payment.source_type,
            "source_id": payment.source_id,
            "amount": payment.amount,
            "payment_date": payment.payment_date.isoformat() if hasattr(payment.payment_date, 'isoformat') else str(payment.payment_date),
            "payment_type": payment.payment_type,
            "payment_status": payment.payment_status,
            "description": payment.description
        }
        
        # Create the payment
        created_payment = await db.create_payment(payment_data)
        return created_payment
        
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating payment"
        )

@router.post("/vehicle", response_model=PaymentResponse)
async def create_vehicle_payment(
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
