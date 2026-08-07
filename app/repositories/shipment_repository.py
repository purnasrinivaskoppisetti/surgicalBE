from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Shipment, ShipmentScanLog


class ShipmentRepository:

    @staticmethod
    async def create_shipment(db: AsyncSession, shipment: Shipment) -> Shipment:
        db.add(shipment)
        await db.commit()
        await db.refresh(shipment)
        return shipment

    @staticmethod
    async def get_by_order_id(db: AsyncSession, order_id) -> Shipment | None:
        result = await db.execute(
            select(Shipment).where(Shipment.order_id == order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_awb(db: AsyncSession, awb_number: str) -> Shipment | None:
        result = await db.execute(
            select(Shipment).where(Shipment.tracking_number == awb_number)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def save_scan_logs(db: AsyncSession, shipment_id, scans: list[dict]):
        """Saves scan logs, skipping duplicates."""
        for scan in scans:
            # Check if this exact scan code and timestamp already exist
            existing = await db.execute(
                select(ShipmentScanLog).where(
                    ShipmentScanLog.shipment_id == shipment_id,
                    ShipmentScanLog.scan_code == scan["scan_code"],
                    ShipmentScanLog.scanned_at == scan["scanned_at"]
                )
            )
            if not existing.scalar_one_or_none():
                log = ShipmentScanLog(
                    shipment_id=shipment_id,
                    scan_status=scan["scan_status"],
                    scan_code=scan["scan_code"],
                    scan_type=scan["scan_type"],
                    scan_group_type=scan["scan_group_type"],
                    scanned_location=scan["scanned_location"],
                    scanned_at=scan["scanned_at"]
                )
                db.add(log)

        await db.commit()