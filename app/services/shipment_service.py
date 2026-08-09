# app/services/shipment_service.py

from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import OrderStatus, PaymentStatus, StoreSetting
from app.repositories.order_repository import OrderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.services.bluedart_service import BlueDartService


class ShipmentService:

    @classmethod
    async def process_waybill_generation(cls, db: AsyncSession, order_id: UUID) -> dict:
        """
        Executes the entire waybill workflow:
        1. Validates order state & payment.
        2. Calls BlueDart API.
        3. Persists Shipment record to DB.
        4. Updates Order status to PACKED.
        """
        # 1. Fetch Order Details (user_id=None to allow global access)
        order = await OrderRepository.get_order_details(db, order_id=order_id, user_id=None)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found."
            )

        # 2. Payment Enforcement Check
        is_cod = False
        if hasattr(order, "payments") and order.payments:
            latest_payment = order.payments[-1]
            if hasattr(latest_payment, "payment_method") and latest_payment.payment_method:
                is_cod = str(latest_payment.payment_method).lower() == "cod"

        if not is_cod and order.payment_status != PaymentStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment incomplete. Cannot generate waybill."
            )

        if not order.address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery address missing for order."
            )

        # 3. Fetch Store Warehouse Settings
        store_stmt = select(StoreSetting).limit(1)
        store_result = await db.execute(store_stmt)
        store_setting = store_result.scalar_one_or_none()

        # 4. Generate AWB via Blue Dart API
        waybill_res = await BlueDartService.generate_waybill(
            order=order,
            address=order.address,
            store_setting=store_setting
        )

        awb_no = waybill_res.get("awb_number")
        token_no = waybill_res.get("pickup_token_number")

        # 5. Create or Update Shipment in Database
        shipment = await ShipmentRepository.get_by_order_id(db, order.id)
        if not shipment:
            shipment = await ShipmentRepository.create_shipment(
                db=db,
                order_id=order.id,
                tracking_number=awb_no,
                courier_name="Blue Dart",
                pickup_token_number=token_no,
                cluster_code=waybill_res.get("cluster_code"),
                destination_area=waybill_res.get("destination_area"),
                destination_location=waybill_res.get("destination_location"),
                mps_details=waybill_res.get("mps_details")
            )
        else:
            shipment.tracking_number = awb_no
            shipment.pickup_token_number = token_no
            shipment.cluster_code = waybill_res.get("cluster_code")
            shipment.destination_area = waybill_res.get("destination_area")
            shipment.destination_location = waybill_res.get("destination_location")

        # 6. Update Order Status
        order.status = OrderStatus.PACKED if hasattr(OrderStatus, "PACKED") else "PACKED"
        await db.commit()

        return waybill_res