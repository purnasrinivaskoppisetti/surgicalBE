from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ============================================================
# BASE
# ============================================================

class Base(DeclarativeBase):
    pass


def generate_uuid():
    return uuid.uuid4()


# ============================================================
# ENUMS
# ============================================================

class UserRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InventoryMovementType(str, Enum):
    RESTOCK = "restock"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"


class PaymentMethod(str, Enum):
    COD = "cod"
    CARD = "card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"


class PaymentGateway(str, Enum):
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    CCAVENUE = "ccavenue"
    PHONEPE = "phonepe"


class CouponType(str, Enum):
    PERCENTAGE = "percentage"
    FLAT = "flat"
    FREE_SHIPPING = "free_shipping"


# ============================================================
# USER
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.CUSTOMER,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    addresses = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    orders = relationship(
        "Order",
        back_populates="user",
    )

    cart_items = relationship(
        "CartItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    wishlist_items = relationship(
        "WishlistItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    tickets = relationship(
        "SupportTicket",
        back_populates="user",
        foreign_keys="SupportTicket.user_id",
    )

    assigned_tickets = relationship(
        "SupportTicket",
        foreign_keys="SupportTicket.assigned_to",
    )

    coupon_usages = relationship(
        "CouponUsage",
        back_populates="user",
    )


# ============================================================
# ADDRESS
# ============================================================

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    address_line1: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    address_line2: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    landmark: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
    )

    address_type: Mapped[str] = mapped_column(
        String(20),
        default="home",
        nullable=False,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        back_populates="addresses",
    )

    orders = relationship(
        "Order",
        back_populates="address",
    )


# ============================================================
# CATEGORY
# ============================================================

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    icon: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        index=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    parent = relationship(
        "Category",
        remote_side=[id],
        back_populates="children",
    )

    children = relationship(
        "Category",
        back_populates="parent",
    )

    products = relationship(
        "Product",
        back_populates="category",
    )

    coupons = relationship(
        "CouponCategory",
        back_populates="category",
    )


# ============================================================
# PRODUCT
# ============================================================

class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True,
        nullable=False,
    )

    # NOTE:
    # SKU is now stored at ProductVariant level.
    # A product can have multiple SKUs.
    #
    # Example:
    # T-Shirt-M-001
    # T-Shirt-L-001
    # T-Shirt-XL-001

    brand: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    short_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Base/default price.
    # Variant can override this price.
    mrp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    weight: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        default=0.0,
        nullable=True,
    )

    length: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        default=0.0,
        nullable=True,
    )

    breadth: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        default=0.0,
        nullable=True,
    )

    height: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        default=0.0,
        nullable=True,
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
    )

    status: Mapped[ProductStatus] = mapped_column(
        SQLEnum(ProductStatus),
        default=ProductStatus.ACTIVE,
        index=True,
        nullable=False,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_bestseller: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_new_arrival: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=0,
    )

    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    hsn_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    category = relationship(
        "Category",
        back_populates="products",
    )

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    specifications = relationship(
        "ProductSpecification",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    reviews = relationship(
        "Review",
        back_populates="product",
    )

    cart_items = relationship(
        "CartItem",
        back_populates="product",
    )

    wishlist_items = relationship(
        "WishlistItem",
        back_populates="product",
    )

    order_items = relationship(
        "OrderItem",
        back_populates="product",
    )

    coupons = relationship(
        "CouponProduct",
        back_populates="product",
    )


# ============================================================
# PRODUCT VARIANT
# ============================================================

class ProductVariant(Base):
    """
    Represents one purchasable inventory variant of a product.

    Examples:

    T-Shirt:
        S   -> stock 10
        M   -> stock 20
        L   -> stock 15
        XL  -> stock 5

    Shirt:
        38 -> stock 10
        40 -> stock 20
        42 -> stock 15
        44 -> stock 8

    Shoes:
        7 -> stock 10
        8 -> stock 15
        9 -> stock 20

    Color + Size:

        M + Red  -> stock 10
        M + Blue -> stock 5
        L + Red  -> stock 8
    """

    __tablename__ = "product_variants"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "size",
            "color",
            name="uq_product_variant_size_color",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # SIZE
    # --------------------------------------------------------
    #
    # Can contain:
    # S, M, L, XL, XXL
    # 38, 40, 42, 44, 46
    # 30, 32, 34, 36
    # 500ml, 1L
    # etc.
    #
    size: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # OTHER ATTRIBUTES
    # --------------------------------------------------------
    #
    # Example:
    #
    # {
    #   "material": "Cotton",
    #   "fit": "Regular",
    #   "style": "Full Sleeve"
    # }
    #

    attributes: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # --------------------------------------------------------
    # SKU
    # --------------------------------------------------------

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------
    #
    # If null, Product.sale_price is used.
    #

    mrp: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    sale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    stock_qty: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Prevent negative inventory
    #
    # This is also checked in service/repository logic.
    #

    reserved_qty: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    product = relationship(
        "Product",
        back_populates="variants",
    )

    cart_items = relationship(
        "CartItem",
        back_populates="variant",
    )

    order_items = relationship(
        "OrderItem",
        back_populates="variant",
    )

    inventory_logs = relationship(
        "InventoryLog",
        back_populates="variant",
        cascade="all, delete-orphan",
    )


# ============================================================
# PRODUCT IMAGE
# ============================================================

class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    product = relationship(
        "Product",
        back_populates="images",
    )


# ============================================================
# PRODUCT SPECIFICATION
# ============================================================

class ProductSpecification(Base):
    __tablename__ = "product_specifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    spec_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    spec_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    product = relationship(
        "Product",
        back_populates="specifications",
    )


# ============================================================
# REVIEW
# ============================================================

class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="review_rating_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    review_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus),
        default=ReviewStatus.PENDING,
        index=True,
    )

    admin_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        back_populates="reviews",
    )

    product = relationship(
        "Product",
        back_populates="reviews",
    )


# ============================================================
# CART ITEM
# ============================================================

class CartItem(Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            "variant_id",
            name="uq_cart_user_product_variant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        back_populates="cart_items",
    )

    product = relationship(
        "Product",
        back_populates="cart_items",
    )

    variant = relationship(
        "ProductVariant",
        back_populates="cart_items",
    )


# ============================================================
# WISHLIST
# ============================================================

class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_wishlist_user_product",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        back_populates="wishlist_items",
    )

    product = relationship(
        "Product",
        back_populates="wishlist_items",
    )


# ============================================================
# COUPON
# ============================================================

class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    coupon_type: Mapped[CouponType] = mapped_column(
        SQLEnum(CouponType),
        nullable=False,
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    minimum_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    usage_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    used_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    is_first_order_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    products = relationship(
        "CouponProduct",
        back_populates="coupon",
        cascade="all, delete-orphan",
    )

    categories = relationship(
        "CouponCategory",
        back_populates="coupon",
        cascade="all, delete-orphan",
    )

    usages = relationship(
        "CouponUsage",
        back_populates="coupon",
        cascade="all, delete-orphan",
    )

    orders = relationship(
        "Order",
        back_populates="coupon",
    )


# ============================================================
# COUPON PRODUCT
# ============================================================

class CouponProduct(Base):
    __tablename__ = "coupon_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "coupons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    coupon = relationship(
        "Coupon",
        back_populates="products",
    )

    product = relationship(
        "Product",
        back_populates="coupons",
    )


# ============================================================
# COUPON CATEGORY
# ============================================================

class CouponCategory(Base):
    __tablename__ = "coupon_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "coupons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    coupon = relationship(
        "Coupon",
        back_populates="categories",
    )

    category = relationship(
        "Category",
        back_populates="coupons",
    )


# ============================================================
# COUPON USAGE
# ============================================================

class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coupons.id"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    coupon = relationship(
        "Coupon",
        back_populates="usages",
    )

    user = relationship(
        "User",
        back_populates="coupon_usages",
    )

    order = relationship(
        "Order",
        back_populates="coupon_usage",
    )


# ============================================================
# ORDER
# ============================================================

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    address_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "addresses.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coupons.id"),
        nullable=True,
    )

    coupon_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PENDING,
        index=True,
        nullable=False,
    )

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        index=True,
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    shipping_charge: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancel_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        back_populates="orders",
    )

    address = relationship(
        "Address",
        back_populates="orders",
    )

    coupon = relationship(
        "Coupon",
        back_populates="orders",
    )

    coupon_usage = relationship(
        "CouponUsage",
        back_populates="order",
        uselist=False,
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    tickets = relationship(
        "SupportTicket",
        back_populates="order",
    )

    payments = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    shipments = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan",
    )


# ============================================================
# ORDER ITEM
# ============================================================

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    # --------------------------------------------------------
    # SNAPSHOT DATA
    # --------------------------------------------------------
    #
    # These values should never change after the order is made.
    #

    product_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    product_sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Store the selected size at purchase time.
    #
    # Example:
    # M
    # XL
    # 44
    # 46
    #

    size: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Store selected color at purchase time.

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Store other variant information.

    variant_attributes: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    order = relationship(
        "Order",
        back_populates="items",
    )

    product = relationship(
        "Product",
        back_populates="order_items",
    )

    variant = relationship(
        "ProductVariant",
        back_populates="order_items",
    )


# ============================================================
# PAYMENT
# ============================================================

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod),
        nullable=False,
    )

    payment_gateway: Mapped[PaymentGateway | None] = mapped_column(
        SQLEnum(PaymentGateway),
        nullable=True,
    )

    gateway_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    gateway_order_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        index=True,
        nullable=False,
    )

    payment_request_data: Mapped[dict | None] = mapped_column(
        JSON,
        default=None,
        nullable=True,
    )

    payment_response_data: Mapped[dict | None] = mapped_column(
        JSON,
        default=None,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    refund_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    order = relationship(
        "Order",
        back_populates="payments",
    )


# ============================================================
# INVENTORY LOG
# ============================================================

class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    movement_type: Mapped[InventoryMovementType] = mapped_column(
        SQLEnum(InventoryMovementType),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    product = relationship(
        "Product",
    )

    variant = relationship(
        "ProductVariant",
        back_populates="inventory_logs",
    )


# ============================================================
# SUPPORT TICKET
# ============================================================

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(TicketPriority),
        default=TicketPriority.MEDIUM,
    )

    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus),
        default=TicketStatus.OPEN,
        index=True,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="tickets",
    )

    order = relationship(
        "Order",
        back_populates="tickets",
    )

    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )


# ============================================================
# TICKET MESSAGE
# ============================================================

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "support_tickets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attachment_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    ticket = relationship(
        "SupportTicket",
        back_populates="messages",
    )


# ============================================================
# BANNER
# ============================================================

class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subtitle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mobile_image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    redirect_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )


# ============================================================
# STORE SETTINGS
# ============================================================

class StoreSetting(Base):
    __tablename__ = "store_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    support_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    support_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    gst_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    delivery_charge: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    free_shipping_threshold: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    cod_charge: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    timezone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    company_logo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# ============================================================
# ORDER STATUS HISTORY
# ============================================================

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


# ============================================================
# SHIPMENT
# ============================================================

class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    courier_name: Mapped[str] = mapped_column(
        String(100),
        default="Blue Dart",
    )

    # --------------------------------------------------------
    # TRACKING / AWB
    # --------------------------------------------------------

    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    # --------------------------------------------------------
    # BLUE DART PRODUCT METADATA
    # --------------------------------------------------------

    product_code: Mapped[str | None] = mapped_column(
        String(10),
        default="A",
    )

    sub_product_code: Mapped[str | None] = mapped_column(
        String(10),
        default="P",
    )

    pack_type: Mapped[str | None] = mapped_column(
        String(10),
        default="L",
    )

    # --------------------------------------------------------
    # BLUE DART RESPONSE
    # --------------------------------------------------------

    pickup_token_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    cluster_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    origin_area: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    destination_area: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    destination_location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    mps_details: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # --------------------------------------------------------
    # PDF / LABEL
    # --------------------------------------------------------

    awb_pdf_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    label_pdf_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    awb_print_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # DIMENSIONS / WEIGHT
    # --------------------------------------------------------

    actual_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        default=0.5,
        nullable=True,
    )

    length: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    breadth: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    height: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    piece_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status: Mapped[str | None] = mapped_column(
        String(100),
        default="PICKUP HAS BEEN REGISTERED",
    )

    status_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    last_scanned_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    estimated_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    shipped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    order = relationship(
        "Order",
        back_populates="shipments",
    )

    scan_logs = relationship(
        "ShipmentScanLog",
        back_populates="shipment",
        cascade="all, delete-orphan",
    )


# ============================================================
# SHIPMENT SCAN LOG
# ============================================================

class ShipmentScanLog(Base):
    __tablename__ = "shipment_scan_logs"

    __table_args__ = (
        UniqueConstraint(
            "shipment_id",
            "scan_code",
            "scanned_at",
            name="uq_shipment_scan_event",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "shipments.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    scan_status: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    scan_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    scan_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    scan_group_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    scanned_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    shipment = relationship(
        "Shipment",
        back_populates="scan_logs",
    )