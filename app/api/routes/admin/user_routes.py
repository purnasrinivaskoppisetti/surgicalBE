from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query
)

from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from app.core.database import (
    get_db
)

from app.services.admin.user_service import (
    UserService
)

router = APIRouter(
    prefix="/admin/customers",
    tags=["Admin Customers"]
)


@router.get("")
async def get_customers(
    page: int = Query(1),
    page_size: int = Query(20),
    search: str | None = None,
    db: AsyncSession = Depends(get_db)
):

    return {
        "success": True,
        "status_code": 200,
        "data": await UserService.get_customers(
            db,
            page,
            page_size,
            search
        )
    }


@router.get("/{customer_id}")
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db)
):

    return {
        "success": True,
        "status_code": 200,
        "data": await UserService.get_customer(
            db,
            customer_id
        )
    }