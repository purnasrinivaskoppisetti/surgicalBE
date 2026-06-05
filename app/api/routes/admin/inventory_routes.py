from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from app.core.database import (
    get_db
)

from app.services.admin.inventory_service import (
    InventoryService
)

router = APIRouter(
    prefix="/admin/inventory",
    tags=["Admin Inventory"]
)


@router.get("")
async def get_inventory(
    db: AsyncSession = Depends(get_db)
):

    return {
        "success": True,
        "status_code": 200,
        "data": await InventoryService.get_inventory_dashboard(
            db
        )
    }