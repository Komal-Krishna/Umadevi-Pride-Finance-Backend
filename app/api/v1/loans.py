from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.base import (
    LoanCreate, LoanUpdate, LoanResponse,
    PaymentCreate, PaymentResponse
)
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/loans", tags=["Loans"])

@router.get("/", response_model=List[LoanResponse])
async def get_loans(
    is_closed: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all loan records with optional closed status filter"""
    try:
        loans = await db.get_loans(is_closed)
        
        # Calculate extended days and payment totals for each loan record
        for loan in loans:
            loan["extended_days"] = await calculate_extended_days(loan)
            loan["total_payments"], loan["pending_amount"] = await calculate_payment_totals(
                db, "loan", loan["id"]
            )
        
        return loans
    except Exception as e:
        logger.error(f"Error fetching loans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching loans"
        )

@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get a specific loan record by ID"""
    try:
        loans = await db.get_loans()
        loan = next((l for l in loans if l["id"] == loan_id), None)
        
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan record not found"
            )
        
        # Calculate extended days and payment totals
        loan["extended_days"] = await calculate_extended_days(loan)
        loan["total_payments"], loan["pending_amount"] = await calculate_payment_totals(
            db, "loan", loan_id
        )
        
        return loan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching loan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching loan"
        )

@router.post("/", response_model=LoanResponse)
async def create_loan(
    loan: LoanCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new loan record"""
    try:
        loan_data = loan.dict()
        loan_data["is_closed"] = False
        loan_data["created_at"] = datetime.utcnow()
        
        created_loan = await db.create_loan(loan_data)
        
        if not created_loan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating loan record"
            )
        
        return created_loan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating loan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating loan record"
        )

@router.put("/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: int,
    loan_update: LoanUpdate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Update an existing loan record"""
    try:
        # Check if loan record exists
        loans = await db.get_loans()
        existing_loan = next((l for l in loans if l["id"] == loan_id), None)
        
        if not existing_loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan record not found"
            )
        
        # Update loan record
        update_data = {k: v for k, v in loan_update.dict().items() if v is not None}
        updated_loan = await db.update_loan(loan_id, update_data)
        
        if not updated_loan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating loan record"
            )
        
        return updated_loan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating loan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating loan record"
        )

@router.post("/{loan_id}/close")
async def close_loan(
    loan_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Close a loan record"""
    try:
        success = await db.close_loan(loan_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error closing loan record"
            )
        
        return {"message": "Loan record closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing loan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing loan record"
        )

@router.post("/{loan_id}/payments", response_model=PaymentResponse)
async def create_loan_payment(
    loan_id: int,
    payment: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a payment record for a loan"""
    try:
        payment_data = payment.dict()
        payment_data["source_type"] = "loan"
        payment_data["source_id"] = loan_id
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
        logger.error(f"Error creating loan payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating payment"
        )

async def calculate_extended_days(loan: dict) -> Optional[int]:
    """Calculate extended days beyond exact months"""
    try:
        if loan["is_closed"]:
            return None
        
        borrowing_date = loan["date_of_borrowing"]
        if isinstance(borrowing_date, str):
            borrowing_date = datetime.strptime(borrowing_date, "%Y-%m-%d").date()
        
        today = date.today()
        
        # Calculate months difference
        months_diff = (today.year - borrowing_date.year) * 12 + (today.month - borrowing_date.month)
        
        # Calculate expected end date based on payment frequency
        if loan["payment_frequency"] == "monthly":
            expected_months = months_diff
        elif loan["payment_frequency"] == "bimonthly":
            expected_months = months_diff * 2
        elif loan["payment_frequency"] == "quarterly":
            expected_months = months_diff * 3
        
        # Calculate expected end date
        expected_end_date = borrowing_date.replace(day=1)
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
