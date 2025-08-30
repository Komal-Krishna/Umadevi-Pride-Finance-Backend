from supabase import create_client, Client
from app.config import settings
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.service_client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom SQL query"""
        try:
            response = self.service_client.rpc('exec_sql', {
                'query': query,
                'params': params or {}
            }).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    async def get_vehicles(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get vehicles with optional closed status filter"""
        try:
            query = self.supabase.table('vehicles').select('*')
            if is_closed is not None:
                query = query.eq('is_closed', is_closed)
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching vehicles: {e}")
            return []
    
    async def get_outside_interest(self, is_closed: bool = None) -> List[Dict[str, Any]]:
        """Get outside interest records with optional closed status filter"""
        try:
            query = self.supabase.table('outside_interest').select('*')
            if is_closed is not None:
                query = query.eq('is_closed', is_closed)
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching outside interest: {e}")
            return []
    
    async def get_payments(self, source_type: str = None, source_id: int = None) -> List[Dict[str, Any]]:
        """Get payments with optional filters"""
        try:
            query = self.supabase.table('payments').select('*')
            if source_type:
                query = query.eq('source_type', source_type)
            if source_id:
                query = query.eq('source_id', source_id)
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching payments: {e}")
            return []
    
    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vehicle record"""
        try:
            response = self.supabase.table('vehicles').insert(vehicle_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            return {}
    
    async def create_outside_interest(self, interest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new outside interest record"""
        try:
            response = self.supabase.table('outside_interest').insert(interest_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating outside interest: {e}")
            return {}
    
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment record"""
        try:
            response = self.supabase.table('payments').insert(payment_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return {}
    
    async def update_vehicle(self, vehicle_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vehicle record"""
        try:
            response = self.supabase.table('vehicles').update(update_data).eq('id', vehicle_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error updating vehicle: {e}")
            return {}
    
    async def update_outside_interest(self, interest_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an outside interest record"""
        try:
            response = self.supabase.table('outside_interest').update(update_data).eq('id', interest_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error updating outside interest: {e}")
            return {}
    
    async def close_vehicle(self, vehicle_id: int) -> bool:
        """Close a vehicle record"""
        try:
            response = self.supabase.table('vehicles').update({
                'is_closed': True,
                'closure_date': 'now()'
            }).eq('id', vehicle_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error closing vehicle: {e}")
            return False
    
    async def close_outside_interest(self, interest_id: int) -> bool:
        """Close an outside interest record"""
        try:
            response = self.supabase.table('outside_interest').update({
                'is_closed': True,
                'closure_date': 'now()'
            }).eq('id', interest_id).execute()
            return bool(response.data)
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
