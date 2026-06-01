# =============================================================================
# SURGICAL WORLD - MODELS.PY (COMPLETE)
# FastAPI + SQLAlchemy 2.0 + PostgreSQL
# =============================================================================

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

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# =============================================================================
# BASE
# =============================================================================

class Base(DeclarativeBase):
    pass


def generate_uuid():
    return uuid.uuid4()


# =============================================================================
# ENUMS
# =============================================================================

class UserRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


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


# =============================================================================
# USER
# =============================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.CUSTOMER,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships

    addresses = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    orders = relationship(
        "Order",
        back_populates="user"
    )

    cart_items = relationship(
        "CartItem",
        back_populates="user"
    )

    wishlist_items = relationship(
        "WishlistItem",
        back_populates="user"
    )

    reviews = relationship(
        "Review",
        back_populates="user"
    )

    tickets = relationship(
        "SupportTicket",
        back_populates="user",
        foreign_keys="SupportTicket.user_id"
    )

    assigned_tickets = relationship(
        "SupportTicket",
        foreign_keys="SupportTicket.assigned_to"
    )


# =============================================================================
# ADDRESS
# =============================================================================

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    full_name: Mapped[str] = mapped_column(
        String(255)
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    phone: Mapped[str] = mapped_column(
        String(20)
    )

    address_line1: Mapped[str] = mapped_column(
        String(500)
    )

    address_line2: Mapped[str | None] = mapped_column(
        String(500)
    )

    landmark: Mapped[str | None] = mapped_column(
        String(255)
    )

    city: Mapped[str] = mapped_column(
        String(100)
    )

    state: Mapped[str] = mapped_column(
        String(100)
    )

    pincode: Mapped[str] = mapped_column(
        String(10)
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="India"
    )

    address_type: Mapped[str] = mapped_column(
        String(20),
        default="home"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="addresses"
    )

    orders = relationship(
        "Order",
        back_populates="address"
    )

# =============================================================================
# CATEGORY
# =============================================================================

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="SET NULL"
        )
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        index=True
    )

    description: Mapped[str | None] = mapped_column(
        Text
    )

    image_url: Mapped[str | None] = mapped_column(
        Text
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    parent = relationship(
        "Category",
        remote_side=[id],
        back_populates="children"
    )

    children = relationship(
        "Category",
        back_populates="parent"
    )

    products = relationship(
        "Product",
        back_populates="category"
    )


# =============================================================================
# PRODUCT
# =============================================================================

class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="SET NULL"
        )
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    slug: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True
    )

    brand: Mapped[str | None] = mapped_column(
        String(255)
    )

    description: Mapped[str | None] = mapped_column(
        Text
    )

    short_description: Mapped[str | None] = mapped_column(
        String(500)
    )

    mrp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    gst_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=18
    )

    stock_qty: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        Text,
        default=None
    )

    status: Mapped[ProductStatus] = mapped_column(
        SQLEnum(ProductStatus),
        default=ProductStatus.ACTIVE,
        index=True
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_bestseller: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_new_arrival: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=0
    )

    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(255)
    )

    hsn_code: Mapped[str | None] = mapped_column(
        String(50)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    category = relationship(
        "Category",
        back_populates="products"
    )

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    specifications = relationship(
        "ProductSpecification",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    reviews = relationship(
        "Review",
        back_populates="product"
    )

    inventory_logs = relationship(
        "InventoryLog",
        back_populates="product"
    )

    cart_items = relationship(
        "CartItem",
        back_populates="product"
    )

    wishlist_items = relationship(
        "WishlistItem",
        back_populates="product"
    )

    order_items = relationship(
        "OrderItem",
        back_populates="product"
    )


# =============================================================================
# PRODUCT IMAGES
# =============================================================================

class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE"
        )
    )

    image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    product = relationship(
        "Product",
        back_populates="images"
    )


# =============================================================================
# PRODUCT SPECIFICATIONS
# =============================================================================

class ProductSpecification(Base):
    __tablename__ = "product_specifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE"
        )
    )

    spec_key: Mapped[str] = mapped_column(
        String(255)
    )

    spec_value: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    product = relationship(
        "Product",
        back_populates="specifications"
    )


# =============================================================================
# REVIEWS
# =============================================================================

class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="review_rating_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    review_text: Mapped[str | None] = mapped_column(
        Text
    )

    image_url: Mapped[str | None] = mapped_column(
        Text
    )

    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="reviews"
    )

    product = relationship(
        "Product",
        back_populates="reviews"
    )


# =============================================================================
# CART
# =============================================================================

class CartItem(Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE"
        )
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="cart_items"
    )

    product = relationship(
        "Product",
        back_populates="cart_items"
    )


# =============================================================================
# WISHLIST
# =============================================================================

class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE"
        )
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="wishlist_items"
    )

    product = relationship(
        "Product",
        back_populates="wishlist_items"
    )


# =============================================================================
# ORDER
# =============================================================================

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    address_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "addresses.id",
            ondelete="RESTRICT"
        )
    )

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PENDING,
        index=True
    )

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        index=True
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    shipping_charge: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    cancel_reason: Mapped[str | None] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="orders"
    )

    address = relationship(
        "Address",
        back_populates="orders"
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    tickets = relationship(
        "SupportTicket",
        back_populates="order"
    )

    payments = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan"
    )


# =============================================================================
# ORDER ITEMS
# =============================================================================

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE"
        )
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT"
        )
    )

    product_name: Mapped[str] = mapped_column(
        String(500)
    )

    product_sku: Mapped[str] = mapped_column(
        String(100)
    )

    quantity: Mapped[int] = mapped_column(
        Integer
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    gst_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2)
    )

    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    order = relationship(
        "Order",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="order_items"
    )


# =============================================================================
# PAYMENT
# =============================================================================

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod),
        nullable=False
    )

    payment_gateway: Mapped[PaymentGateway | None] = mapped_column(
        SQLEnum(PaymentGateway)
    )

    gateway_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True
    )

    gateway_order_id: Mapped[str | None] = mapped_column(
        String(255)
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR"
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        index=True
    )

    payment_request_data: Mapped[dict | None] = mapped_column(
        JSON,
        default=None
    )

    payment_response_data: Mapped[dict | None] = mapped_column(
        JSON,
        default=None
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text
    )

    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    refund_transaction_id: Mapped[str | None] = mapped_column(
        String(255)
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    order = relationship(
        "Order",
        back_populates="payments"
    )


# =============================================================================
# INVENTORY LOGS
# =============================================================================

class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    movement_type: Mapped[InventoryMovementType] = mapped_column(
        SQLEnum(InventoryMovementType)
    )

    quantity: Mapped[int] = mapped_column(
        Integer
    )

    stock_before: Mapped[int] = mapped_column(
        Integer
    )

    stock_after: Mapped[int] = mapped_column(
        Integer
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(255)
    )

    note: Mapped[str | None] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    product = relationship(
        "Product",
        back_populates="inventory_logs"
    )


# =============================================================================
# SUPPORT TICKETS
# =============================================================================

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="SET NULL"
        )
    )

    subject: Mapped[str] = mapped_column(
        String(255)
    )

    description: Mapped[str] = mapped_column(
        Text
    )

    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(TicketPriority),
        default=TicketPriority.MEDIUM
    )

    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus),
        default=TicketStatus.OPEN,
        index=True
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL"
        )
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="tickets"
    )

    order = relationship(
        "Order",
        back_populates="tickets"
    )

    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )


# =============================================================================
# TICKET MESSAGES
# =============================================================================

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "support_tickets.id",
            ondelete="CASCADE"
        )
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    message: Mapped[str] = mapped_column(
        Text
    )

    attachment_url: Mapped[str | None] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    ticket = relationship(
        "SupportTicket",
        back_populates="messages"
    )


# =============================================================================
# BANNERS
# =============================================================================

class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    title: Mapped[str] = mapped_column(
        String(255)
    )

    subtitle: Mapped[str | None] = mapped_column(
        String(500)
    )

    image_url: Mapped[str] = mapped_column(
        Text
    )

    mobile_image_url: Mapped[str | None] = mapped_column(
        Text
    )

    redirect_url: Mapped[str | None] = mapped_column(
        Text
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )


# =============================================================================
# STORE SETTINGS
# =============================================================================

class StoreSetting(Base):
    __tablename__ = "store_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    company_name: Mapped[str | None] = mapped_column(
        String(255)
    )

    support_email: Mapped[str | None] = mapped_column(
        String(255)
    )

    support_phone: Mapped[str | None] = mapped_column(
        String(20)
    )

    address: Mapped[str | None] = mapped_column(
        Text
    )

    gst_number: Mapped[str | None] = mapped_column(
        String(50)
    )

    delivery_charge: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    free_shipping_threshold: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    gst_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2)
    )

    cod_charge: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2)
    )

    currency: Mapped[str | None] = mapped_column(
        String(10)
    )

    timezone: Mapped[str | None] = mapped_column(
        String(50)
    )

    company_logo_url: Mapped[str | None] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )