import httpx
import json
from datetime import datetime, date
from app.config import settings
from typing import Dict, Any, List, Optional
import logging
import asyncio
import threading
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.supabase_url = settings.supabase_url
            self.supabase_key = settings.supabase_key
            self.service_key = settings.supabase_service_key
            self._client = None
            self._client_lock = asyncio.Lock()
            self._initialized = True
    
    async def get_client(self):
        """Get or create HTTP client with serverless-friendly handling"""
        # Always create a fresh client for serverless environments
        # This prevents event loop closure issues
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json"
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                http2=False  # Disable HTTP/2 for better serverless compatibility
            )
            logger.info("Created new HTTP client for serverless environment")
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime objects to ISO format strings for JSON serialization"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                serialized[key] = value.isoformat()
            elif hasattr(value, 'value'):  # Handle Enum values
                serialized[key] = value.value
            else:
                serialized[key] = value
        return serialized
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, max_retries: int = 2) -> Dict:
        """Make HTTP request to Supabase with serverless-friendly error handling"""
        for attempt in range(max_retries + 1):
            try:
                url = f"{self.supabase_url}/rest/v1/{endpoint}"
                
                # Serialize data if present
                if data:
                    data = self._serialize_data(data)
                
                # Create a fresh client for each request in serverless
                client = httpx.AsyncClient(
                    headers={
                        "apikey": self.service_key,
                        "Authorization": f"Bearer {self.service_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                    http2=False
                )
                
                try:
                    if method.upper() == "GET":
                        response = await client.get(url)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data)
                    elif method.upper() == "PUT":
                        response = await client.put(url, json=data)
                    elif method.upper() == "PATCH":
                        response = await client.patch(url, json=data)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    if response.status_code >= 400:
                        logger.error(f"Supabase error response: {response.text}")
                        response.raise_for_status()
                    
                    response_content = response.json() if response.content else {}
                    logger.info(f"Supabase response content: {response_content}")
                    return response_content
                    
                finally:
                    # Always close the client
                    await client.aclose()
                
            except Exception as e:
                logger.error(f"HTTP request error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                
                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    logger.info(f"Retrying request (attempt {attempt + 2})")
                    continue
                else:
                    # Final attempt failed
                    raise e
    
    async def get_vehicles(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get vehicles with optional closed status filter"""
        try:
            endpoint = "vehicles"
            if is_closed is not None:
                endpoint += f"?is_closed=eq.{is_closed}&deleted_at=is.null"
            else:
                endpoint += "?deleted_at=is.null"
            
            logger.info(f"Fetching vehicles with endpoint: {endpoint}")
            result = await self._make_request("GET", endpoint)
            
            if isinstance(result, list):
                logger.info(f"Successfully fetched {len(result)} vehicles")
                return result
            else:
                logger.warning(f"Unexpected result type: {type(result)}, value: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching vehicles: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return []
    
    async def get_vehicles_with_payments(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get vehicles with payment totals using optimized single query"""
        try:
            # First get all vehicles
            vehicles = await self.get_vehicles(is_closed)
            logger.info(f"Retrieved {len(vehicles)} vehicles from database")
            
            if not vehicles:
                logger.warning("No vehicles found in database")
                return []
            
            # Get all payments for all vehicles in one query
            vehicle_ids = [str(vehicle["id"]) for vehicle in vehicles]
            if not vehicle_ids:
                logger.warning("No vehicle IDs found")
                return vehicles
            
            # Create filter for multiple vehicle IDs
            vehicle_filter = ",".join(vehicle_ids)
            endpoint = f"payments?source_type=eq.vehicle&source_id=in.({vehicle_filter})&select=source_id,amount"
            logger.info(f"Fetching payments for vehicles: {vehicle_ids}")
            
            payments_result = await self._make_request("GET", endpoint)
            payments = payments_result if isinstance(payments_result, list) else []
            logger.info(f"Retrieved {len(payments)} payments from database")
            
            # Calculate payment totals by vehicle
            payment_totals = {}
            for payment in payments:
                vehicle_id = payment.get("source_id")
                amount = payment.get("amount", 0)
                if vehicle_id not in payment_totals:
                    payment_totals[vehicle_id] = 0
                payment_totals[vehicle_id] += amount
            
            # Add payment totals to vehicles
            for vehicle in vehicles:
                vehicle_id = vehicle["id"]
                vehicle["total_payments"] = payment_totals.get(vehicle_id, 0)
            
            logger.info(f"Returning {len(vehicles)} vehicles with payment calculations")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error fetching vehicles with payments: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            # Fallback to basic vehicles without payments
            try:
                fallback_vehicles = await self.get_vehicles(is_closed)
                logger.info(f"Fallback returned {len(fallback_vehicles)} vehicles")
                return fallback_vehicles
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return []
    
    async def get_all_payments_for_vehicles(self, vehicle_ids: List[str]) -> List[Dict[str, Any]]:
        """Get all payments for multiple vehicles in one query"""
        try:
            if not vehicle_ids:
                return []
            
            # Create filter for multiple vehicle IDs - use proper Supabase syntax
            vehicle_filter = ",".join(vehicle_ids)
            endpoint = f"payments?source_type=eq.vehicle&source_id=in.({vehicle_filter})"
            
            result = await self._make_request("GET", endpoint)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error fetching payments for vehicles: {e}")
            return []
    
    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vehicle record"""
        try:
            # Remove any None values that might cause issues
            clean_data = {k: v for k, v in vehicle_data.items() if v is not None}
            
            
            result = await self._make_request("POST", "vehicles", clean_data)
            
            # Supabase returns the created record in the response
            if isinstance(result, list) and len(result) > 0:
                created_vehicle = result[0]
                # Ensure we have the ID from the response
                if "id" in created_vehicle:
                    return created_vehicle
            elif isinstance(result, dict) and "id" in result:
                return result
            
            # If we don't get a proper response with ID, try to fetch the created vehicle
            vehicles = await self.get_vehicles()
            if vehicles:
                # Find the most recent vehicle with matching details
                for vehicle in reversed(vehicles):
                    if (vehicle.get('vehicle_name') == clean_data.get('vehicle_name') and
                        vehicle.get('lend_to') == clean_data.get('lend_to') and
                        vehicle.get('principle_amount') == clean_data.get('principle_amount')):
                        return vehicle
            
            # If we still can't find it, raise an error
            raise Exception("Failed to create vehicle or retrieve created vehicle data")
                
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            raise e
    
    async def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific vehicle by ID"""
        try:
            endpoint = f"vehicles?id=eq.{vehicle_id}&deleted_at=is.null"
            
            # Retry logic for robustness
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = await self._make_request("GET", endpoint)
                    
                    if isinstance(result, list) and len(result) > 0:
                        return result[0]
                    elif isinstance(result, dict):
                        return result
                    else:
                        return None
                        
                except Exception as retry_error:
                    if attempt == max_retries - 1:
                        raise retry_error
                    # Wait a bit before retrying
                    import asyncio
                    await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error fetching vehicle {vehicle_id}: {e}")
            return None

    async def update_vehicle(self, vehicle_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vehicle record"""
        try:
            # Use PATCH for updates as it's more reliable with Supabase
            endpoint = f"vehicles?id=eq.{vehicle_id}"
            
            result = await self._make_request("PATCH", endpoint, update_data)
            
            # Supabase PATCH requests often return empty responses on success
            # We'll always try to fetch the updated vehicle to confirm the update worked
            
            # Small delay to ensure database commit
            await asyncio.sleep(0.1)
            
            # Fetch the updated vehicle with all fields
            vehicle_endpoint = f"vehicles?id=eq.{vehicle_id}&deleted_at=is.null"
            updated_vehicle = await self._make_request("GET", vehicle_endpoint)
            
            if isinstance(updated_vehicle, list) and len(updated_vehicle) > 0:
                return updated_vehicle[0]
            elif isinstance(updated_vehicle, dict):
                return updated_vehicle
            else:
                logger.error(f"Database: No vehicle data found after update for ID {vehicle_id}")
                logger.error(f"Database: This might indicate the vehicle was deleted or the update failed")
                return {}
                
        except Exception as e:
            logger.error(f"Database: Error updating vehicle {vehicle_id}: {e}")
            # Check if it's a specific Supabase error
            if "400 Bad Request" in str(e):
                logger.error(f"Database: Supabase rejected the update request - check data format and constraints")
            elif "404 Not Found" in str(e):
                logger.error(f"Database: Vehicle {vehicle_id} not found in database")
            elif "500 Internal Server Error" in str(e):
                logger.error(f"Database: Supabase internal error during update")
            return {}
    
    async def close_vehicle(self, vehicle_id: int) -> bool:
        """Close a vehicle record"""
        try:
            update_data = {
                "is_closed": True,
                "closure_date": "now()"
            }
            endpoint = f"vehicles?id=eq.{vehicle_id}"
            result = await self._make_request("PATCH", endpoint, update_data)
            
            # Supabase PATCH operations return empty responses on success
            # The fact that we got here without an exception means it succeeded
            return True
        except Exception as e:
            logger.error(f"Error closing vehicle: {e}")
            return False
    
    async def soft_delete_vehicle(self, vehicle_id: int) -> bool:
        """Soft delete a vehicle record"""
        try:
            update_data = {
                "deleted_at": "now()"
            }
            endpoint = f"vehicles?id=eq.{vehicle_id}"
            
            result = await self._make_request("PATCH", endpoint, update_data)
            
            # Supabase PATCH operations return empty responses on success
            # The fact that we got here without an exception means it succeeded
            return True
                
        except Exception as e:
            logger.error(f"Database: Error soft deleting vehicle {vehicle_id}: {e}")
            return False
    
    async def get_outside_interest(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get outside interest records with optional closed status filter"""
        try:
            endpoint = "outside_interest"
            if is_closed is not None:
                endpoint += f"?is_closed=eq.{is_closed}&deleted_at=is.null"
            else:
                endpoint += "?deleted_at=is.null"
                
            result = await self._make_request("GET", endpoint)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error fetching outside interest: {e}")
            return []
    
    async def get_payments(self, source_type: str = None, source_id: int = None) -> List[Dict[str, Any]]:
        """Get payments with optional filters"""
        try:
            endpoint = "payments"
            if source_type:
                endpoint += f"?source_type=eq.{source_type}"
            if source_id:
                endpoint += f"&source_id=eq.{source_id}"
                
            result = await self._make_request("GET", endpoint)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error fetching payments: {e}")
            return []
    
    async def get_all_payments_for_vehicles(self) -> List[Dict[str, Any]]:
        """Get all payments for vehicles in one batch request"""
        try:
            endpoint = "payments?source_type=eq.vehicle"
            result = await self._make_request("GET", endpoint)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error fetching all vehicle payments: {e}")
            return []
    
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment record"""
        try:
            result = await self._make_request("POST", "payments", payment_data)
            
            # Supabase often returns empty response on successful creation
            # In this case, we'll return the original data with a success indicator
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict) and result:
                return result
            elif isinstance(result, dict) and not result:
                # Empty response from Supabase - this is normal for successful creation
                from datetime import datetime
                return {
                    "id": 0,  # Placeholder ID (integer)
                    "source_type": payment_data["source_type"],
                    "source_id": payment_data["source_id"],
                    "payment_type": payment_data["payment_type"],
                    "payment_date": payment_data["payment_date"],
                    "amount": payment_data["amount"],
                    "description": payment_data["description"],
                    "payment_status": payment_data["payment_status"],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise e  # Re-raise the exception
    
    async def close_outside_interest(self, interest_id: int) -> bool:
        """Close an outside interest record"""
        try:
            update_data = {
                "is_closed": True,
                "closure_date": "now()"
            }
            endpoint = f"outside_interest?id=eq.{interest_id}"
            result = await self._make_request("PATCH", endpoint, update_data)
            
            # Supabase PATCH operations return empty responses on success
            # The fact that we got here without an exception means it succeeded
            return True
        except Exception as e:
            logger.error(f"Error closing outside interest: {e}")
            return False

def get_db() -> DatabaseManager:
    """Get the singleton database instance with connection pooling"""
    return DatabaseManager()
