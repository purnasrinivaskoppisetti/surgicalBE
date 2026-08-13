from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.dependencies import (
    get_current_user,
)

from app.schemas.customer.cart_schema import (
    AddToCartRequest,
    ApplyCouponRequest,
)

from app.services.customer.cart_service import (
    CartService,
)


router = APIRouter(
    prefix="/customer/cart",
    tags=["Cart"],
)


# ============================================================
# ADD TO CART
# ============================================================

@router.post("/add/{product_id}")
async def add_to_cart(

    product_id: UUID,

    payload: AddToCartRequest,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),

):

    return await CartService.add_to_cart(

        db=db,

        user_id=current_user["sub"],

        product_id=product_id,

        variant_id=payload.variant_id,

        quantity=payload.quantity,

    )


# ============================================================
# GET CART
# ============================================================

@router.get("")
async def get_cart(

    page: int = Query(
        1,
        ge=1,
    ),

    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),

):

    return await CartService.get_cart(

        db=db,

        user_id=current_user["sub"],

        page=page,

        page_size=page_size,

    )


# ============================================================
# REMOVE FROM CART
# ============================================================

@router.delete(
    "/remove/{product_id}/{variant_id}"
)
async def remove_from_cart(

    product_id: UUID,

    variant_id: UUID,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),

):

    return await CartService.remove_from_cart(

        db=db,

        user_id=current_user["sub"],

        product_id=product_id,

        variant_id=variant_id,

    )


# ============================================================
# CART SUMMARY
# ============================================================

@router.get("/summary")
async def get_cart_summary(

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),

):

    return await CartService.get_cart_summary(

        db=db,

        user_id=current_user["sub"],

    )


# ============================================================
# APPLY COUPON
# ============================================================

@router.post("/apply-coupon")
async def apply_coupon(

    payload: ApplyCouponRequest,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),

):

    return await CartService.apply_coupon(

        db=db,

        user_id=current_user["sub"],

        coupon_code=payload.coupon_code,

    )


# ============================================================
# CLEAR CART
# ============================================================

@router.delete("")
async def clear_cart(

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),

):

    return await CartService.clear_cart(

        db=db,

        user_id=current_user["sub"],

    )