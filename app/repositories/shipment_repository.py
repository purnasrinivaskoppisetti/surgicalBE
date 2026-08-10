from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Shipment,
    ShipmentScanLog,
)


class ShipmentRepository:

    # ============================================================
    # CREATE SHIPMENT
    # ============================================================

    @staticmethod
    async def create_shipment(
        db: AsyncSession,
        shipment: Shipment,
    ) -> Shipment:
        """
        Create a shipment record.

        The service controls the transaction, so this method
        intentionally uses flush() instead of commit().
        """

        db.add(shipment)

        # Execute INSERT without committing.
        await db.flush()

        # Load generated values such as ID.
        await db.refresh(shipment)

        return shipment

    # ============================================================
    # GET SHIPMENT BY ORDER ID
    # ============================================================

    @staticmethod
    async def get_by_order_id(
        db: AsyncSession,
        order_id,
    ) -> Optional[Shipment]:

        result = await db.execute(
            select(Shipment)
            .where(
                Shipment.order_id == order_id
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # GET SHIPMENT BY AWB
    # ============================================================

    @staticmethod
    async def get_by_awb(
        db: AsyncSession,
        awb_number: str,
    ) -> Optional[Shipment]:

        result = await db.execute(
            select(Shipment)
            .where(
                Shipment.tracking_number == awb_number
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # SAVE SHIPMENT SCAN LOGS
    # ============================================================

    @staticmethod
    async def save_scan_logs(
        db: AsyncSession,
        shipment_id,
        scans: list[dict],
    ):
        """
        Save shipment scan logs.

        Duplicate records are skipped based on:
        - shipment_id
        - scan_code
        - scanned_at
        """

        for scan in scans:

            existing_result = await db.execute(
                select(ShipmentScanLog)
                .where(
                    ShipmentScanLog.shipment_id
                    == shipment_id,

                    ShipmentScanLog.scan_code
                    == scan["scan_code"],

                    ShipmentScanLog.scanned_at
                    == scan["scanned_at"],
                )
            )

            existing = (
                existing_result
                .scalar_one_or_none()
            )

            if existing:
                continue

            log = ShipmentScanLog(
                shipment_id=shipment_id,

                scan_status=(
                    scan["scan_status"]
                ),

                scan_code=(
                    scan["scan_code"]
                ),

                scan_type=(
                    scan["scan_type"]
                ),

                scan_group_type=(
                    scan["scan_group_type"]
                ),

                scanned_location=(
                    scan["scanned_location"]
                ),

                scanned_at=(
                    scan["scanned_at"]
                ),
            )

            db.add(log)

        await db.flush()

    # ============================================================
    # GET ALL SHIPMENTS FOR ORDER
    # ============================================================

    @staticmethod
    async def get_all_by_order_id(
        db: AsyncSession,
        order_id,
    ) -> list[Shipment]:

        result = await db.execute(
            select(Shipment)
            .where(
                Shipment.order_id == order_id
            )
            .order_by(
                Shipment.created_at.desc()
            )
        )

        return result.scalars().all()

    # ============================================================
    # GET SHIPMENT BY ID
    # ============================================================

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        shipment_id,
    ) -> Optional[Shipment]:

        result = await db.execute(
            select(Shipment)
            .where(
                Shipment.id == shipment_id
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # UPDATE SHIPMENT STATUS
    # ============================================================

    @staticmethod
    async def update_status(
        db: AsyncSession,
        shipment_id,
        status: str,
    ) -> Optional[Shipment]:

        shipment = (
            await ShipmentRepository.get_by_id(
                db,
                shipment_id,
            )
        )

        if not shipment:
            return None

        shipment.status = status

        await db.flush()

        return shipment

    # ============================================================
    # UPDATE TRACKING INFORMATION
    # ============================================================

    @staticmethod
    async def update_tracking(
        db: AsyncSession,
        shipment_id,
        tracking_number: Optional[str] = None,
        status: Optional[str] = None,
        last_scanned_location: Optional[str] = None,
        last_scanned_at=None,
        estimated_delivery=None,
    ) -> Optional[Shipment]:

        shipment = (
            await ShipmentRepository.get_by_id(
                db,
                shipment_id,
            )
        )

        if not shipment:
            return None

        if tracking_number is not None:
            shipment.tracking_number = (
                tracking_number
            )

        if status is not None:
            shipment.status = status

        if last_scanned_location is not None:
            shipment.last_scanned_location = (
                last_scanned_location
            )

        if last_scanned_at is not None:
            shipment.last_scanned_at = (
                last_scanned_at
            )

        if estimated_delivery is not None:
            shipment.estimated_delivery = (
                estimated_delivery
            )

        await db.flush()

        return shipment

    # ============================================================
    # GET SHIPMENT SCAN LOGS
    # ============================================================

    @staticmethod
    async def get_scan_logs(
        db: AsyncSession,
        shipment_id,
    ) -> list[ShipmentScanLog]:

        result = await db.execute(
            select(ShipmentScanLog)
            .where(
                ShipmentScanLog.shipment_id
                == shipment_id
            )
            .order_by(
                ShipmentScanLog.scanned_at.desc()
            )
        )

        return result.scalars().all()

    # ============================================================
    # GET LATEST SCAN
    # ============================================================

    @staticmethod
    async def get_latest_scan(
        db: AsyncSession,
        shipment_id,
    ) -> Optional[ShipmentScanLog]:

        result = await db.execute(
            select(ShipmentScanLog)
            .where(
                ShipmentScanLog.shipment_id
                == shipment_id
            )
            .order_by(
                ShipmentScanLog.scanned_at.desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    # ============================================================
    # DELETE SHIPMENT
    # ============================================================

    @staticmethod
    async def delete_shipment(
        db: AsyncSession,
        shipment_id,
    ) -> bool:

        shipment = (
            await ShipmentRepository.get_by_id(
                db,
                shipment_id,
            )
        )

        if not shipment:
            return False

        await db.delete(shipment)

        await db.flush()

        return True