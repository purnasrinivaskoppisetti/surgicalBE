from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.repositories.order_repository import OrderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.services.bluedart_service import BlueDartService

router = APIRouter(prefix="/shipping", tags=["Customer Shipping"])


@router.get("/check-serviceability")
async def check_pincode(pincode: str = Query(..., example="534281")):
    """
    Public / Checkout Endpoint.
    Allows customers to check if Blue Dart delivers to their pincode.
    """
    return await BlueDartService.check_serviceability(pincode=pincode)


@router.get("/track/{awb_number}")
async def track_shipment_by_awb(
    awb_number: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public / Customer Endpoint.
    Allows customers to track live updates for an AWB number.
    """
    tracking_data = await BlueDartService.track_shipment(awb_number)

    # Sync scans to database if shipment exists in local DB
    shipment = await ShipmentRepository.get_by_awb(db, awb_number)
    if shipment and tracking_data.get("scans"):
        shipment.status = tracking_data["status"]
        latest = tracking_data["scans"][0]
        shipment.last_scanned_location = latest["scanned_location"]
        shipment.last_scanned_at = latest["scanned_at"]

        await ShipmentRepository.save_scan_logs(db, shipment.id, tracking_data["scans"])

    return {
        "success": True,
        "data": tracking_data
    }


@router.get("/track-order/{order_id}")
async def track_my_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Customer Endpoint.
    Allows logged-in customers to track their order using `order_id`.
    """
    order = await OrderRepository.get_order_details(
        db=db,
        order_id=order_id,
        user_id=current_user.id
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    shipment = await ShipmentRepository.get_by_order_id(db, order_id)
    if not shipment or not shipment.tracking_number:
        return {
            "success": True,
            "message": "Order is processing. Pickup registration pending.",
            "data": {"status": "Processing"}
        }

    # Fetch live Blue Dart tracking
    tracking_data = await BlueDartService.track_shipment(shipment.tracking_number)

    if tracking_data.get("scans"):
        shipment.status = tracking_data["status"]
        latest = tracking_data["scans"][0]
        shipment.last_scanned_location = latest["scanned_location"]
        shipment.last_scanned_at = latest["scanned_at"]

        await ShipmentRepository.save_scan_logs(db, shipment.id, tracking_data["scans"])

    return {
        "success": True,
        "data": tracking_data
    }