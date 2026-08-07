from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    category_id: UUID
    name: str
    sku: str
    brand: str | None = None
    description: str | None = None
    short_description: str | None = None

    mrp: Decimal = Field(gt=0)
    sale_price: Decimal = Field(gt=0)
    stock_qty: int = Field(default=0, ge=0)

    # --- Added Package Dimensions for Shipping ---
    weight: Decimal = Field(default=Decimal("0.50"), ge=0, description="Weight in kg")
    length: Decimal = Field(default=Decimal("10.00"), ge=0, description="Length in cm")
    breadth: Decimal = Field(default=Decimal("10.00"), ge=0, description="Breadth in cm")
    height: Decimal = Field(default=Decimal("10.00"), ge=0, description="Height in cm")

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

    mrp: Decimal | None = Field(default=None, gt=0)
    sale_price: Decimal | None = Field(default=None, gt=0)
    stock_qty: int | None = Field(default=None, ge=0)

    # --- Added Optional Dimensions for Update ---
    weight: Decimal | None = Field(default=None, ge=0)
    length: Decimal | None = Field(default=None, ge=0)
    breadth: Decimal | None = Field(default=None, ge=0)
    height: Decimal | None = Field(default=None, ge=0)

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

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(BaseModel):
    id: UUID
    category_id: UUID | None = None
    category_name: str | None = None
    name: str
    slug: str
    sku: str
    brand: str | None = None
    description: str | None = None
    short_description: str | None = None

    mrp: Decimal
    sale_price: Decimal
    discount_percentage: int = 0
    stock_qty: int
    stock_status: str | None = None

    # --- Dimensions Returned in Response ---
    weight: Decimal = Decimal("0.0")
    length: Decimal = Decimal("0.0")
    breadth: Decimal = Decimal("0.0")
    height: Decimal = Decimal("0.0")

    thumbnail_url: str | None = None
    manufacturer: str | None = None
    hsn_code: str | None = None
    rating: float = 0
    review_count: int = 0

    is_featured: bool
    is_bestseller: bool
    is_new_arrival: bool

    images: list[ProductImageResponse] = []
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)