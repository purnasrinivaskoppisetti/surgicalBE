from app.core.database import AsyncSessionLocal

from app.services.shipping_tracking_service import (
    ShippingTrackingService,
)


async def update_shipments_job():

    print(
        "========================================"
    )

    print(
        "Blue Dart tracking job started"
    )

    print(
        "========================================"
    )

    async with AsyncSessionLocal() as db:

        result = await (
            ShippingTrackingService
            .update_all_shipments(db)
        )

        print(
            "Blue Dart tracking result:"
        )

        print(result)

    print(
        "Blue Dart tracking job completed"
    )