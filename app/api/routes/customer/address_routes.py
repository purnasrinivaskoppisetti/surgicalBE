from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.schemas.customer.address_schema import (
    AddressCreateRequest
)

from app.services.customer.address_service import (
    AddressService
)

router = APIRouter(
    prefix="/customer/addresses",
    tags=["Customer Address"]
)


@router.post("")
async def create_address(
    payload: AddressCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await AddressService.create_address(
        db=db,
        user_id=current_user["sub"],
        payload=payload
    )