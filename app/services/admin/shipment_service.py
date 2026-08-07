# app/services/admin/shipment_service.py
import uuid
from sqlalchemy.orm import Session
from app.models.models import Order, Shipment
from app.core.config import settings
from app.services.integrations.bluedart_client import bluedart_client

class AdminShipmentService:
    @staticmethod
    async def generate_waybill(db: Session, order_id: str) -> Shipment:
        """Fetch order, call Blue Dart GenerateWayBill, update database."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise Exception("Order not found")

        address = order.address
        if not address:
            raise Exception("Delivery address missing for order")

        payload = {
            "Request": {
                "Shipper": {
                    "OriginArea": settings.BLUEDART_ORIGIN_AREA,
                    "CustomerCode": settings.BLUEDART_CUSTOMER_CODE,
                    "CustomerName": "Surgical World Warehouse",
                    "CustomerAddress1": "Plot 12, Industrial Area",
                    "CustomerPincode": "500001",
                    "CustomerMobile": "9999999999",
                    "isToPayCustomer": False
                },
                "Consignee": {
                    "ConsigneeName": address.full_name[:30],
                    "ConsigneeAddress1": address.address_line1[:30],
                    "ConsigneeAddress2": (address.address_line2 or "")[:30],
                    "ConsigneePincode": address.pincode,
                    "ConsigneeMobile": address.phone,
                    "ConsigneeEmailID": address.email or "customer@example.com"
                },
                "Services": {
                    "ProductCode": settings.BLUEDART_DEFAULT_PRODUCT,
                    "SubProductCode": "C" if order.payment_status != "paid" else "P",
                    "ProductType": 1,
                    "PieceCount": len(order.items),
                    "ActualWeight": 1.5,
                    "CreditReferenceNo": str(order.order_number),
                    "DeclaredValue": float(order.total_amount),
                    "PickupDate": f"/Date({int(order.created_at.timestamp() * 1000)})/",
                    "PickupTime": "1600"
                }
            },
            "Profile": bluedart_client.get_profile_object()
        }

        res = await bluedart_client.request_json("/in/transportation/waybill/v1/GenerateWayBill", payload)
        
        if res.get("IsError", False):
            errors = res.get("Status", [])
            msg = errors[0].get("StatusInformation") if errors else "Waybill Generation Failed"
            raise Exception(f"Blue Dart Error: {msg}")

        awb_no = res.get("AWBNo")
        dest_area = res.get("DestinationArea")
        dest_loc = res.get("DestinationLocation")

        shipment = Shipment(
            id=uuid.uuid4(),
            order_id=order.id,
            courier_name="Blue Dart",
            tracking_number=awb_no,
            origin_area=settings.BLUEDART_ORIGIN_AREA,
            destination_area=dest_area,
            destination_location=dest_loc,
            status="MANIFESTED"
        )
        db.add(shipment)
        db.commit()
        db.refresh(shipment)
        
        return shipment

    @staticmethod
    async def register_pickup(db: Session, shipment_id: str, pickup_date: str) -> str:
        """Register courier pickup for manifested shipment."""
        shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if not shipment or not shipment.tracking_number:
            raise Exception("Valid shipment with AWB required for pickup registration")

        payload = {
            "Request": {
                "ProductCode": "A",
                "AreaCode": settings.BLUEDART_ORIGIN_AREA,
                "CustomerCode": settings.BLUEDART_CUSTOMER_CODE,
                "CustomerName": "Surgical World",
                "CustomerAddress1": "Plot 12, Industrial Area",
                "CustomerPincode": "500001",
                "CustomerTelephoneNumber": "04012345678",
                "MobileTelNo": "9999999999",
                "ShipmentPickupDate": pickup_date,
                "ShipmentPickupTime": "15:00",
                "NumberofPieces": 1,
                "WeightofShipment": 1.5,
                "AWBNo": [shipment.tracking_number]
            },
            "Profile": bluedart_client.get_profile_object()
        }

        res = await bluedart_client.request_json("/in/transportation/pickup/v1/RegisterPickup", payload)
        
        if res.get("IsError"):
            raise Exception("Failed to register pickup with Blue Dart")

        token = res.get("TokenNumber")
        shipment.pickup_token_number = token
        db.commit()
        return token