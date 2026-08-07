from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_admin
from app.models.models import OrderStatus, Shipment
from app.repositories.order_repository import OrderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.services.bluedart_service import BlueDartService

router = APIRouter(prefix="/admin/shipping", tags=["Admin Shipping"])


@router.post("/generate-waybill/{order_id}")
async def generate_order_waybill(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Admin Only Endpoint.
    Generates a Blue Dart Waybill/AWB and registers the pickup.
    """
    order = await OrderRepository.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    existing_shipment = await ShipmentRepository.get_by_order_id(db, order_id)
    if existing_shipment:
        return {
            "success": True,
            "message": "Waybill already generated",
            "awb_number": existing_shipment.tracking_number
        }

    # Generate Waybill via Blue Dart API
    waybill_res = await BlueDartService.generate_waybill(order, order.address)

    # Save shipment to database
    new_shipment = Shipment(
        order_id=order.id,
        courier_name="Blue Dart",
        tracking_number=waybill_res["awb_number"],
        pickup_token_number=waybill_res["pickup_token_number"],
        cluster_code=waybill_res["cluster_code"],
        origin_area=order.address.pincode,
        destination_area=waybill_res["destination_area"],
        destination_location=waybill_res["destination_location"],
        mps_details=waybill_res["mps_details"],
        status="PICKUP HAS BEEN REGISTERED"
    )

    await ShipmentRepository.create_shipment(db, new_shipment)

    # Update Order Status to SHIPPED
    order.status = OrderStatus.SHIPPED
    await db.commit()

    return {
        "success": True,
        "message": "Waybill generated successfully",
        "data": {
            "awb_number": new_shipment.tracking_number,
            "pickup_token": new_shipment.pickup_token_number
        }
    }