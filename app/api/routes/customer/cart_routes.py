from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.dependencies import (
    get_current_user
)

from app.schemas.customer.cart_schema import (
    AddToCartRequest
)

from app.services.customer.cart_service import (
    CartService
)

router = APIRouter(
    prefix="/customer/cart",
    tags=["Cart"]
)


@router.post("/{product_id}")
async def add_to_cart(
    product_id: UUID,
    payload: AddToCartRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return await CartService.add_to_cart(
        db=db,
        user_id=current_user["sub"],
        product_id=product_id,
        quantity=payload.quantity
    )


@router.get("")
async def get_cart(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return await CartService.get_cart(
        db=db,
        user_id=current_user["sub"],
        page=page,
        page_size=page_size
    )


@router.delete("/{product_id}")
async def remove_from_cart(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return await CartService.remove_from_cart(
        db=db,
        user_id=current_user["sub"],
        product_id=product_id
    )