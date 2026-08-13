from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# ADD TO CART
# ============================================================

class AddToCartRequest(BaseModel):

    variant_id: UUID

    quantity: int = Field(
        default=1,
        ge=1,
    )


# ============================================================
# APPLY COUPON
# ============================================================

class ApplyCouponRequest(BaseModel):

    coupon_code: str = Field(
        min_length=1,
        max_length=100,
    )