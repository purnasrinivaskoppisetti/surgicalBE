from uuid import UUID
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# PRODUCT VARIANT
# ============================================================

class ProductVariantCreate(BaseModel):
    """
    One purchasable variant of a product.

    Examples:
        S / M / L / XL
        38 / 40 / 42 / 44
        Red + M
        Blue + L
    """

    size: str | None = None
    color: str | None = None

    sku: str

    mrp: Decimal | None = Field(
        default=None,
        gt=0
    )

    sale_price: Decimal | None = Field(
        default=None,
        gt=0
    )

    stock_qty: int = Field(
        default=0,
        ge=0
    )

    attributes: dict | None = None


class ProductVariantUpdate(BaseModel):

    id: UUID | None = None

    size: str | None = None
    color: str | None = None

    sku: str | None = None

    mrp: Decimal | None = Field(
        default=None,
        gt=0
    )

    sale_price: Decimal | None = Field(
        default=None,
        gt=0
    )

    stock_qty: int | None = Field(
        default=None,
        ge=0
    )

    attributes: dict | None = None

    is_active: bool | None = None


class ProductVariantResponse(BaseModel):

    id: UUID

    product_id: UUID

    size: str | None = None
    color: str | None = None

    sku: str

    mrp: Decimal | None = None
    sale_price: Decimal | None = None

    stock_qty: int

    reserved_qty: int = 0

    available_qty: int = 0

    stock_status: str

    attributes: dict | None = None

    is_active: bool

    created_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# PRODUCT CREATE
# ============================================================

class ProductCreate(BaseModel):

    category_id: UUID

    name: str

    brand: str | None = None

    description: str | None = None

    short_description: str | None = None

    # --------------------------------------------------------
    # DEFAULT PRODUCT PRICE
    # --------------------------------------------------------

    mrp: Decimal = Field(
        gt=0
    )

    sale_price: Decimal = Field(
        gt=0
    )

    # --------------------------------------------------------
    # VARIANTS
    # --------------------------------------------------------

    variants: list[ProductVariantCreate] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # PACKAGE DIMENSIONS
    # --------------------------------------------------------

    weight: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        description="Weight in kg"
    )

    length: Decimal = Field(
        default=Decimal("10.00"),
        ge=0,
        description="Length in cm"
    )

    breadth: Decimal = Field(
        default=Decimal("10.00"),
        ge=0,
        description="Breadth in cm"
    )

    height: Decimal = Field(
        default=Decimal("10.00"),
        ge=0,
        description="Height in cm"
    )

    manufacturer: str | None = None

    hsn_code: str | None = None

    is_featured: bool = False

    is_bestseller: bool = False

    is_new_arrival: bool = False


# ============================================================
# PRODUCT UPDATE
# ============================================================

class ProductUpdate(BaseModel):

    category_id: UUID | None = None

    name: str | None = None

    brand: str | None = None

    description: str | None = None

    short_description: str | None = None

    mrp: Decimal | None = Field(
        default=None,
        gt=0
    )

    sale_price: Decimal | None = Field(
        default=None,
        gt=0
    )

    # --------------------------------------------------------
    # VARIANTS
    # --------------------------------------------------------

    variants: list[ProductVariantUpdate] | None = None

    # --------------------------------------------------------
    # DIMENSIONS
    # --------------------------------------------------------

    weight: Decimal | None = Field(
        default=None,
        ge=0
    )

    length: Decimal | None = Field(
        default=None,
        ge=0
    )

    breadth: Decimal | None = Field(
        default=None,
        ge=0
    )

    height: Decimal | None = Field(
        default=None,
        ge=0
    )

    manufacturer: str | None = None

    hsn_code: str | None = None

    is_featured: bool | None = None

    is_bestseller: bool | None = None

    is_new_arrival: bool | None = None


# ============================================================
# IMAGE RESPONSE
# ============================================================

class ProductImageResponse(BaseModel):

    id: UUID | None = None

    image_url: str

    is_primary: bool = False

    sort_order: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# PRODUCT RESPONSE
# ============================================================

class ProductResponse(BaseModel):

    id: UUID

    category_id: UUID | None = None

    category_name: str | None = None

    name: str

    slug: str

    brand: str | None = None

    description: str | None = None

    short_description: str | None = None

    mrp: Decimal

    sale_price: Decimal

    discount_percentage: int = 0

    # --------------------------------------------------------
    # TOTAL STOCK
    # --------------------------------------------------------

    stock_qty: int = 0

    stock_status: str | None = None

    # --------------------------------------------------------
    # VARIANTS
    # --------------------------------------------------------

    variants: list[ProductVariantResponse] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # DIMENSIONS
    # --------------------------------------------------------

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

    images: list[ProductImageResponse] = Field(
        default_factory=list
    )

    created_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True
    )