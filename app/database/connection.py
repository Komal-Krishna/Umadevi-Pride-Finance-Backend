import httpx
import json
from datetime import datetime, date
from app.config import settings
from typing import Dict, Any, List, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.supabase_url = settings.supabase_url
        self.supabase_key = settings.supabase_key
        self.service_key = settings.supabase_service_key
        self._client = None
    
    @property
    def client(self):
        """Get or create HTTP client with proper async handling"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json"
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
                http2=True
            )
            logger.info("Created new HTTP client connection")
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP client connection closed")
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            # Simple query to test connection
            result = await self._make_request("GET", "vehicles?limit=1")
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
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
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request to Supabase with improved error handling"""
        try:
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            logger.debug(f"Making {method.upper()} request to: {url}")
            
            # Serialize data if present
            if data:
                data = self._serialize_data(data)
                logger.debug(f"Request data: {data}")
            
            # Ensure client is available
            client = self.client
            
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
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code >= 400:
                logger.error(f"Supabase error response ({response.status_code}): {response.text}")
                response.raise_for_status()
            
            # Handle empty responses
            if not response.content:
                logger.warning("Empty response content received")
                return {}
            
            try:
                response_content = response.json()
                logger.debug(f"Response content type: {type(response_content)}")
                return response_content
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                logger.error(f"Raw response: {response.text}")
                return {}
            
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            # Reset client to force reconnection
            await self.close()
            raise e
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error: {e}")
            raise e
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            raise e
    
    async def get_vehicles(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get vehicles with optional closed status filter"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                endpoint = "vehicles"
                if is_closed is not None:
                    endpoint += f"?is_closed=eq.{is_closed}&deleted_at=is.null"
                else:
                    endpoint += "?deleted_at=is.null"
                
                logger.info(f"Fetching vehicles (attempt {attempt + 1}/{max_retries})")
                result = await self._make_request("GET", endpoint)
                
                if isinstance(result, list):
                    logger.info(f"Successfully fetched {len(result)} vehicles")
                    return result
                else:
                    logger.warning(f"Unexpected result type: {type(result)}, value: {result}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return []
                    
            except Exception as e:
                logger.error(f"Error fetching vehicles (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return []
        
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

# Global database instance - will be initialized when needed
db = None

def get_db():
    global db
    if db is None:
        db = DatabaseManager()
    return db
