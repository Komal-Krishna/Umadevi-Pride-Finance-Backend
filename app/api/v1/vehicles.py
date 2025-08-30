from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.base import (
    VehicleCreate, VehicleUpdate, VehicleResponse, 
    PaymentCreate, PaymentResponse
)
from app.api.dependencies import get_current_user, get_database
from app.database.connection import DatabaseManager
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

@router.get("/", response_model=List[VehicleResponse])
async def get_vehicles(
    is_closed: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all vehicles with optional closed status filter"""
    try:
        vehicles = await db.get_vehicles(is_closed)
        
        # Calculate extended days and payment totals for each vehicle
        for vehicle in vehicles:
            vehicle["extended_days"] = await calculate_extended_days(vehicle)
            vehicle["total_payments"], vehicle["pending_amount"] = await calculate_payment_totals(
                db, "vehicle", vehicle["id"]
            )
        
        return vehicles
    except Exception as e:
        logger.error(f"Error fetching vehicles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching vehicles"
        )

@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get a specific vehicle by ID"""
    try:
        vehicles = await db.get_vehicles()
        vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)
        
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        # Calculate extended days and payment totals
        vehicle["extended_days"] = await calculate_extended_days(vehicle)
        vehicle["total_payments"], vehicle["pending_amount"] = await calculate_payment_totals(
            db, "vehicle", vehicle_id
        )
        
        return vehicle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching vehicle"
        )

@router.post("/", response_model=VehicleResponse)
async def create_vehicle(
    vehicle: VehicleCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new vehicle record"""
    try:
        vehicle_data = vehicle.dict()
        vehicle_data["is_closed"] = False
        vehicle_data["created_at"] = datetime.utcnow()
        
        created_vehicle = await db.create_vehicle(vehicle_data)
        
        if not created_vehicle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating vehicle record"
            )
        return created_vehicle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating vehicle record: {str(e)}"
        )

@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Update an existing vehicle record"""
    try:
        # Check if vehicle exists
        vehicles = await db.get_vehicles()
        existing_vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)
        
        if not existing_vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        # Update vehicle
        update_data = {k: v for k, v in vehicle_update.dict().items() if v is not None}
        updated_vehicle = await db.update_vehicle(vehicle_id, update_data)
        
        if not updated_vehicle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating vehicle"
            )
        
        return updated_vehicle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating vehicle"
        )

@router.post("/{vehicle_id}/close")
async def close_vehicle(
    vehicle_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Close a vehicle record"""
    try:
        success = await db.close_vehicle(vehicle_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error closing vehicle record"
            )
        
        return {"message": "Vehicle record closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing vehicle record"
        )

@router.delete("/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Soft delete a vehicle record"""
    try:
        success = await db.soft_delete_vehicle(vehicle_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting vehicle record"
            )
        
        return {"message": "Vehicle record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting vehicle record"
        )

@router.post("/{vehicle_id}/payments", response_model=PaymentResponse)
async def create_vehicle_payment(
    vehicle_id: int,
    payment: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a payment record for a vehicle"""
    try:
        payment_data = payment.dict()
        payment_data["source_type"] = "vehicle"
        payment_data["source_id"] = vehicle_id
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
        logger.error(f"Error creating vehicle payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating payment"
        )

async def calculate_extended_days(vehicle: dict) -> Optional[int]:
    """Calculate extended days beyond exact months"""
    try:
        if vehicle["is_closed"]:
            return None
        
        lending_date = vehicle["date_of_lending"]
        if isinstance(lending_date, str):
            lending_date = datetime.strptime(lending_date, "%Y-%m-%d").date()
        
        today = date.today()
        
        # Calculate months difference
        months_diff = (today.year - lending_date.year) * 12 + (today.month - lending_date.month)
        
        # Calculate expected end date
        if vehicle["payment_frequency"] == "monthly":
            expected_months = months_diff
        elif vehicle["payment_frequency"] == "bimonthly":
            expected_months = months_diff * 2
        elif vehicle["payment_frequency"] == "quarterly":
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
