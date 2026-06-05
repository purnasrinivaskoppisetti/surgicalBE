from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.admin.dashboard_service import DashboardService

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin Dashboard"]
)


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db)
):
    return {
        "success": True,
        "status_code": 200,
        "message": "Dashboard fetched successfully",
        "data": await DashboardService.get_dashboard(db)
    }