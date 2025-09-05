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

@router.get("/getAll", response_model=List[VehicleResponse])
async def get_all_vehicles(
    is_closed: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get all vehicles with payment calculations"""
    try:
        logger.info(f"Fetching vehicles with is_closed filter: {is_closed}")
        
        # Perform health check first
        if not await db.health_check():
            logger.error("Database health check failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
        vehicles = await db.get_vehicles(is_closed)
        logger.info(f"Retrieved {len(vehicles)} vehicles from database")
        
        if not vehicles:
            logger.warning("No vehicles found in database")
            return []
        
        # Calculate payment totals for each vehicle
        enhanced_vehicles = []
        for vehicle in vehicles:
            try:
                # Get payments for this vehicle
                payments = await db.get_payments("vehicle", vehicle["id"])
                total_payments = sum(payment.get("amount", 0) for payment in payments)
                pending_amount = max(0, vehicle.get("principle_amount", 0) - total_payments)
                
                # Add calculated fields
                vehicle["total_payments"] = total_payments
                vehicle["pending_amount"] = pending_amount
                vehicle["is_active"] = not vehicle.get("is_closed", False)
                
                enhanced_vehicles.append(vehicle)
            except Exception as e:
                logger.error(f"Error calculating payments for vehicle {vehicle.get('id')}: {e}")
                # Add default values if calculation fails
                vehicle["total_payments"] = 0
                vehicle["pending_amount"] = vehicle.get("principle_amount", 0)
                vehicle["is_active"] = not vehicle.get("is_closed", False)
                enhanced_vehicles.append(vehicle)
        
        logger.info(f"Returning {len(enhanced_vehicles)} enhanced vehicles")
        return enhanced_vehicles
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching vehicles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching vehicles"
        )

@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle_by_id(
    vehicle_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Get a specific vehicle by ID with payment calculations"""
    try:
        vehicle = await db.get_vehicle_by_id(vehicle_id)
        
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} not found"
            )
        
        # Calculate payment totals
        try:
            payments = await db.get_payments("vehicle", vehicle_id)
            total_payments = sum(payment.get("amount", 0) for payment in payments)
            pending_amount = max(0, vehicle.get("principle_amount", 0) - total_payments)
            
            # Add calculated fields
            vehicle["total_payments"] = total_payments
            vehicle["pending_amount"] = pending_amount
            vehicle["is_active"] = not vehicle.get("is_closed", False)
        except Exception as e:
            logger.error(f"Error calculating payments for vehicle {vehicle_id}: {e}")
            # Add default values if calculation fails
            vehicle["total_payments"] = 0
            vehicle["pending_amount"] = vehicle.get("principle_amount", 0)
            vehicle["is_active"] = not vehicle.get("is_closed", False)
        
        return vehicle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vehicle {vehicle_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching vehicle"
        )

@router.post("/create", response_model=VehicleResponse)
async def create_vehicle(
    vehicle: VehicleCreate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new vehicle"""
    try:
        # Only send the exact fields that Supabase expects
        vehicle_data = {
            "vehicle_name": vehicle.vehicle_name,
            "principle_amount": vehicle.principle_amount,
            "rent": vehicle.rent,
            "payment_frequency": vehicle.payment_frequency,
            "date_of_lending": vehicle.date_of_lending.isoformat() if hasattr(vehicle.date_of_lending, 'isoformat') else str(vehicle.date_of_lending),
            "lend_to": vehicle.lend_to
        }
        
        
        # Don't send updated_at, created_at, is_closed - let database handle these
        # Don't send any None values
        
        created_vehicle = await db.create_vehicle(vehicle_data)
        
        if not created_vehicle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating vehicle"
            )
        return created_vehicle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating vehicle: {str(e)}"
        )

@router.put("/updateDetails/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle_details(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Update vehicle details"""
    try:
        # First check if the vehicle exists
        existing_vehicle = await db.get_vehicle_by_id(vehicle_id)
        
        if not existing_vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} not found"
            )
        
        # Filter out None values and format data properly
        update_data = {}
        for key, value in vehicle_update.dict().items():
            if value is not None:
                if key == "date_of_lending" and hasattr(value, 'isoformat'):
                    update_data[key] = value.isoformat()
                else:
                    update_data[key] = value
        
        # Don't send updated_at, created_at, is_closed - let database handle these
        # Don't send any None values
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid data provided for update"
            )
        
        logger.info(f"Updating vehicle {vehicle_id} with data: {update_data}")
        
        updated_vehicle = await db.update_vehicle(vehicle_id, update_data)
        
        logger.info(f"Update result: {updated_vehicle}")
        
        if not updated_vehicle:
            logger.error(f"Update failed for vehicle {vehicle_id} - no data returned")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database update failed - no vehicle data returned"
            )
        return updated_vehicle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating vehicle: {str(e)}"
        )

@router.delete("/delete/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Delete a vehicle"""
    try:
        # First check if the vehicle exists
        existing_vehicle = await db.get_vehicle_by_id(vehicle_id)
        
        if not existing_vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} not found"
            )
        
        logger.info(f"Attempting to delete vehicle {vehicle_id}")
        
        success = await db.soft_delete_vehicle(vehicle_id)
        
        if not success:
            logger.error(f"Delete operation failed for vehicle {vehicle_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database delete operation failed"
            )
        
        logger.info(f"Successfully deleted vehicle {vehicle_id}")
        return {"message": "Vehicle deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting vehicle {vehicle_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting vehicle: {str(e)}"
        )

@router.post("/close/{vehicle_id}")
async def close_vehicle(
    vehicle_id: int,
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """Close a vehicle"""
    try:
        success = await db.close_vehicle(vehicle_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error closing vehicle"
            )
        return {"message": "Vehicle closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing vehicle"
        )
