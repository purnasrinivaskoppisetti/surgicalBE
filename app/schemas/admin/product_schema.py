from uuid import UUID
from decimal import Decimal
from datetime import datetime

from uuid import UUID
from decimal import Decimal
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict
)





class ProductCreate(BaseModel):

    category_id: UUID

    name: str
    sku: str

    brand: str | None = None

    description: str | None = None
    short_description: str | None = None

    mrp: Decimal
    sale_price: Decimal

    gst_percent: Decimal = Decimal("18")

    stock_qty: int = 0

    manufacturer: str | None = None
    hsn_code: str | None = None

    is_featured: bool = False
    is_bestseller: bool = False
    is_new_arrival: bool = False


class ProductUpdate(BaseModel):

    category_id: UUID | None = None

    name: str | None = None
    sku: str | None = None

    brand: str | None = None

    description: str | None = None
    short_description: str | None = None

    mrp: Decimal | None = None
    sale_price: Decimal | None = None

    gst_percent: Decimal | None = None

    stock_qty: int | None = None

    manufacturer: str | None = None
    hsn_code: str | None = None

    is_featured: bool | None = None
    is_bestseller: bool | None = None
    is_new_arrival: bool | None = None




class ProductImageResponse(BaseModel):

    id: UUID | None = None
    image_url: str
    is_primary: bool = False
    sort_order: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )


class ProductResponse(BaseModel):

    id: UUID
    category_id: UUID

    name: str
    slug: str

    sku: str

    brand: str | None = None

    description: str | None = None
    short_description: str | None = None

    mrp: Decimal
    sale_price: Decimal

    gst_percent: Decimal

    stock_qty: int

    thumbnail_url: str | None = None

    manufacturer: str | None = None
    hsn_code: str | None = None

    is_featured: bool
    is_bestseller: bool
    is_new_arrival: bool

    images: list[ProductImageResponse] = []

    created_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True
    )