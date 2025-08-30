import httpx
import json
from datetime import datetime, date
from app.config import settings
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.supabase_url = settings.supabase_url
        self.supabase_key = settings.supabase_key
        self.service_key = settings.supabase_service_key
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
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
        """Make HTTP request to Supabase"""
        try:
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            
            # Serialize data if present
            if data:
                data = self._serialize_data(data)
            
            if method.upper() == "GET":
                response = await self.client.get(url)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data)
            elif method.upper() == "PUT":
                response = await self.client.put(url, json=data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            raise e
    
    async def get_vehicles(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get vehicles with optional closed status filter"""
        try:
            endpoint = "vehicles"
            if is_closed is not None:
                endpoint += f"?is_closed=eq.{is_closed}&deleted_at=is.null"
            else:
                endpoint += "?deleted_at=is.null"
                
            result = await self._make_request("GET", endpoint)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error fetching vehicles: {e}")
            return []
    
    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vehicle record"""
        try:
            # Remove any None values that might cause issues
            clean_data = {k: v for k, v in vehicle_data.items() if v is not None}
            
            result = await self._make_request("POST", "vehicles", clean_data)
            
            # Supabase returns the created record in the response
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict):
                return result
            else:
                # If no data returned, try to fetch the created vehicle
                vehicles = await self.get_vehicles()
                if vehicles:
                    # Find the most recent vehicle with matching details
                    for vehicle in reversed(vehicles):
                        if (vehicle.get('vehicle_name') == clean_data.get('vehicle_name') and
                            vehicle.get('lend_to') == clean_data.get('lend_to')):
                            return vehicle
                
                # Return a success response even if we can't get the data
                return {
                    "id": None,
                    "vehicle_name": clean_data.get('vehicle_name'),
                    "principle_amount": clean_data.get('principle_amount'),
                    "rent": clean_data.get('rent'),
                    "payment_frequency": clean_data.get('payment_frequency'),
                    "date_of_lending": clean_data.get('date_of_lending'),
                    "lend_to": clean_data.get('lend_to'),
                    "is_closed": clean_data.get('is_closed', False),
                    "message": "Vehicle created successfully"
                }
                
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            raise e
    
    async def update_vehicle(self, vehicle_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vehicle record"""
        try:
            endpoint = f"vehicles?id=eq.{vehicle_id}"
            result = await self._make_request("PUT", endpoint, update_data)
            
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict):
                return result
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error updating vehicle: {e}")
            return {}
    
    async def close_vehicle(self, vehicle_id: int) -> bool:
        """Close a vehicle record"""
        try:
            update_data = {
                "is_closed": True,
                "closure_date": "now()"
            }
            endpoint = f"vehicles?id=eq.{vehicle_id}"
            result = await self._make_request("PUT", endpoint, update_data)
            return bool(result)
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
            result = await self._make_request("PUT", endpoint, update_data)
            return bool(result)
        except Exception as e:
            logger.error(f"Error soft deleting vehicle: {e}")
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
    
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment record"""
        try:
            result = await self._make_request("POST", "payments", payment_data)
            
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict):
                return result
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return {}
    
    async def close_outside_interest(self, interest_id: int) -> bool:
        """Close an outside interest record"""
        try:
            update_data = {
                "is_closed": True,
                "closure_date": "now()"
            }
            endpoint = f"outside_interest?id=eq.{interest_id}"
            result = await self._make_request("PUT", endpoint, update_data)
            return bool(result)
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
