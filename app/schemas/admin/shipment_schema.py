# app/schemas/admin/shipment_schema.py
from pydantic import BaseModel
from typing import Optional

class WaybillCreateRequest(BaseModel):
    order_id: str

class WaybillResponse(BaseModel):
    shipment_id: str
    order_id: str
    awb_number: str
    destination_area: Optional[str] = None
    destination_location: Optional[str] = None
    status: str

class PickupRegisterRequest(BaseModel):
    shipment_id: str
    pickup_date: str  # YYYY-MM-DD
    pickup_time: str = "14:00"
    piece_count: int = 1
    weight_kg: float = 1.0

class PickupResponse(BaseModel):
    token_number: str
    status: str