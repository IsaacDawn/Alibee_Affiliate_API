# Statistics models and schemas
from pydantic import BaseModel
from typing import Optional, Dict, Any

class StatsResponse(BaseModel):
    totalProducts: int = 0
    savedProducts: int = 0
    totalSearches: int = 0

class SystemStatusResponse(BaseModel):
    db: str
    message: Optional[str] = None
    ali_client: str
    ali_api_status: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, Any]
