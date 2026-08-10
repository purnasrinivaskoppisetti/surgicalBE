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

        The service controls the transaction, therefore this method
        uses flush() instead of commit().
        """

        db.add(shipment)

        # Execute INSERT without committing.
        await db.flush()

        # Load generated values such as UUID.
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
            .order_by(
                Shipment.created_at.desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

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

        return list(
            result.scalars().all()
        )

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
                Shipment.tracking_number
                == awb_number
            )
        )

        return result.scalar_one_or_none()

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
    # GET ALL SHIPMENT SCAN LOGS
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

        return list(
            result.scalars().all()
        )

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
    # SAVE SHIPMENT SCAN LOGS
    # ============================================================

    @staticmethod
    async def save_scan_logs(
        db: AsyncSession,
        shipment_id,
        scans: list[dict],
    ) -> None:
        """
        Save Blue Dart shipment scan events.

        Duplicate scan events are skipped using:
            shipment_id
            scan_code
            scanned_at

        The final transaction is controlled by the service.
        """

        if not scans:
            return

        for scan in scans:

            # ----------------------------------------------------
            # EXTRACT VALUES SAFELY
            # ----------------------------------------------------

            scan_code = (
                scan.get("scan_code")
                or scan.get("code")
            )

            scan_status = (
                scan.get("scan_status")
                or scan.get("status")
                or "UNKNOWN"
            )

            scan_type = (
                scan.get("scan_type")
                or scan.get("type")
            )

            scan_group_type = (
                scan.get("scan_group_type")
            )

            scanned_location = (
                scan.get("scanned_location")
                or scan.get("location")
            )

            scanned_at = (
                scan.get("scanned_at")
            )

            # ----------------------------------------------------
            # TIMESTAMP IS REQUIRED FOR DUPLICATE CHECK
            # ----------------------------------------------------

            if scanned_at is None:
                continue

            # ----------------------------------------------------
            # CHECK EXISTING SCAN
            # ----------------------------------------------------

            existing_result = await db.execute(
                select(ShipmentScanLog)
                .where(
                    ShipmentScanLog.shipment_id
                    == shipment_id,

                    ShipmentScanLog.scan_code
                    == scan_code,

                    ShipmentScanLog.scanned_at
                    == scanned_at,
                )
                .limit(1)
            )

            existing = (
                existing_result
                .scalar_one_or_none()
            )

            if existing:
                continue

            # ----------------------------------------------------
            # CREATE SCAN LOG
            # ----------------------------------------------------

            scan_log = ShipmentScanLog(
                shipment_id=shipment_id,

                scan_status=scan_status,

                scan_code=scan_code,

                scan_type=scan_type,

                scan_group_type=scan_group_type,

                scanned_location=scanned_location,

                scanned_at=scanned_at,
            )

            db.add(scan_log)

        # --------------------------------------------------------
        # FLUSH ONLY
        # --------------------------------------------------------

        await db.flush()

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
        status_code: Optional[str] = None,
        last_scanned_location: Optional[str] = None,
        last_scanned_at=None,
        estimated_delivery=None,
        shipped_at=None,
        delivered_at=None,
    ) -> Optional[Shipment]:

        shipment = (
            await ShipmentRepository.get_by_id(
                db,
                shipment_id,
            )
        )

        if not shipment:
            return None

        # --------------------------------------------------------
        # AWB / TRACKING NUMBER
        # --------------------------------------------------------

        if tracking_number is not None:
            shipment.tracking_number = (
                tracking_number
            )

        # --------------------------------------------------------
        # BLUE DART STATUS
        # --------------------------------------------------------

        if status is not None:
            shipment.status = status

        # --------------------------------------------------------
        # BLUE DART STATUS CODE
        # --------------------------------------------------------

        if status_code is not None:
            shipment.status_code = status_code

        # --------------------------------------------------------
        # CURRENT LOCATION
        # --------------------------------------------------------

        if last_scanned_location is not None:
            shipment.last_scanned_location = (
                last_scanned_location
            )

        # --------------------------------------------------------
        # LAST SCAN TIME
        # --------------------------------------------------------

        if last_scanned_at is not None:
            shipment.last_scanned_at = (
                last_scanned_at
            )

        # --------------------------------------------------------
        # ESTIMATED DELIVERY
        # --------------------------------------------------------

        if estimated_delivery is not None:
            shipment.estimated_delivery = (
                estimated_delivery
            )

        # --------------------------------------------------------
        # SHIPPED TIME
        # --------------------------------------------------------

        if shipped_at is not None:
            shipment.shipped_at = (
                shipped_at
            )

        # --------------------------------------------------------
        # DELIVERED TIME
        # --------------------------------------------------------

        if delivered_at is not None:
            shipment.delivered_at = (
                delivered_at
            )

        await db.flush()

        return shipment

    # ============================================================
    # GET CURRENT TRACKING SUMMARY
    # ============================================================

    @staticmethod
    async def get_tracking_summary(
        db: AsyncSession,
        shipment_id,
    ) -> Optional[dict]:

        shipment = (
            await ShipmentRepository.get_by_id(
                db,
                shipment_id,
            )
        )

        if not shipment:
            return None

        latest_scan = (
            await ShipmentRepository
            .get_latest_scan(
                db,
                shipment_id,
            )
        )

        current_location = (
            shipment.last_scanned_location
        )

        current_status = (
            shipment.status
        )

        current_status_code = (
            shipment.status_code
        )

        last_scanned_at = (
            shipment.last_scanned_at
        )

        # --------------------------------------------------------
        # FALLBACK TO LATEST SCAN
        # --------------------------------------------------------

        if latest_scan:

            if not current_status:
                current_status = (
                    latest_scan.scan_status
                )

            if not current_status_code:
                current_status_code = (
                    latest_scan.scan_code
                )

            if not current_location:
                current_location = (
                    latest_scan.scanned_location
                )

            if not last_scanned_at:
                last_scanned_at = (
                    latest_scan.scanned_at
                )

        return {

            "shipment_id":
                str(shipment.id),

            "order_id":
                str(shipment.order_id),

            "courier":
                shipment.courier_name,

            "awb_number":
                shipment.tracking_number,

            "waybill_generated":
                bool(
                    shipment.tracking_number
                ),

            "waybill_status":
                current_status,

            "status":
                current_status,

            "status_code":
                current_status_code,

            "current_location":
                current_location,

            "last_scanned_location":
                shipment.last_scanned_location,

            "last_scanned_at":
                last_scanned_at,

            "estimated_delivery":
                shipment.estimated_delivery,

            "shipped_at":
                shipment.shipped_at,

            "delivered_at":
                shipment.delivered_at,
        }

    # ============================================================
    # GET COMPLETE TRACKING HISTORY
    # ============================================================

    @staticmethod
    async def get_tracking_history(
        db: AsyncSession,
        shipment_id,
    ) -> list[dict]:

        scan_logs = (
            await ShipmentRepository
            .get_scan_logs(
                db,
                shipment_id,
            )
        )

        return [

            {
                "scan_id":
                    str(scan.id),

                "status":
                    scan.scan_status,

                "status_code":
                    scan.scan_code,

                "scan_type":
                    scan.scan_type,

                "scan_group_type":
                    scan.scan_group_type,

                "location":
                    scan.scanned_location,

                "scanned_at":
                    scan.scanned_at,
            }

            for scan in scan_logs
        ]

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