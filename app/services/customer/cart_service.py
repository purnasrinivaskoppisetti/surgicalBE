from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException

from app.models.models import CartItem

from app.repositories.cart_repository import (
    CartRepository
)

from app.repositories.coupon_repository import (
    CouponRepository
)

from app.repositories.setting_repository import (
    SettingRepository
)

from app.repositories.product_repository import (
    ProductRepository
)

from app.utils.pagination import (
    build_pagination
)


class CartService:

    # ============================================================
    # HELPER - GET VARIANT PRICE
    # ============================================================

    @staticmethod
    def _get_variant_price(
        product,
        variant
    ):
        """
        Variant price has priority.

        If variant price is NULL,
        product price will be used.

        Example:

        Product:
            sale_price = 999

        S:
            sale_price = NULL
            => 999

        M:
            sale_price = NULL
            => 999

        L:
            sale_price = 1049
            => 1049
        """

        mrp = (
            variant.mrp
            if variant.mrp is not None
            else product.mrp
        )

        sale_price = (
            variant.sale_price
            if variant.sale_price is not None
            else product.sale_price
        )

        return mrp, sale_price

    # ============================================================
    # ADD TO CART
    # ============================================================

    @staticmethod
    async def add_to_cart(
        db: AsyncSession,
        user_id: UUID,
        product_id: UUID,
        variant_id: UUID,
        quantity: int
    ):

        try:

            # ----------------------------------------------------
            # VALIDATE QUANTITY
            # ----------------------------------------------------

            if quantity <= 0:

                raise HTTPException(
                    status_code=400,
                    detail="Quantity must be greater than zero"
                )

            # ----------------------------------------------------
            # GET PRODUCT
            # ----------------------------------------------------

            product = await ProductRepository.get_by_id(
                db=db,
                product_id=product_id
            )

            if not product:

                raise HTTPException(
                    status_code=404,
                    detail="Product not found"
                )

            # ----------------------------------------------------
            # GET VARIANT
            # ----------------------------------------------------

            variant = await ProductRepository.get_variant_by_id(
                db=db,
                variant_id=variant_id
            )

            if not variant:

                raise HTTPException(
                    status_code=404,
                    detail="Product variant not found"
                )

            # ----------------------------------------------------
            # VERIFY VARIANT BELONGS TO PRODUCT
            # ----------------------------------------------------

            if variant.product_id != product.id:

                raise HTTPException(
                    status_code=400,
                    detail="Selected variant does not belong to this product"
                )

            # ----------------------------------------------------
            # CHECK ACTIVE VARIANT
            # ----------------------------------------------------

            if not variant.is_active:

                raise HTTPException(
                    status_code=400,
                    detail="Selected product variant is not available"
                )

            # ----------------------------------------------------
            # AVAILABLE STOCK
            # ----------------------------------------------------

            available_stock = max(
                0,
                variant.stock_qty - variant.reserved_qty
            )

            if available_stock <= 0:

                raise HTTPException(
                    status_code=400,
                    detail="Selected variant is out of stock"
                )

            # ----------------------------------------------------
            # GET EXISTING CART ITEM
            # ----------------------------------------------------

            existing = (
                await CartRepository.get_by_user_and_variant(
                    db=db,
                    user_id=user_id,
                    product_id=product_id,
                    variant_id=variant_id
                )
            )

            # ----------------------------------------------------
            # IMPORTANT
            #
            # If item already exists, quantity is UPDATED,
            # not added.
            #
            # Example:
            #
            # Existing = 2
            # Request = 5
            #
            # Final = 5
            # ----------------------------------------------------

            if existing:

                if quantity > available_stock:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Only {available_stock} item(s) "
                            "available for this variant"
                        )
                    )

                existing.quantity = quantity

                await CartRepository.update(
                    db=db,
                    cart_item=existing
                )

                return {
                    "success": True,
                    "status_code": 200,
                    "message": "Cart quantity updated successfully",
                    "data": {
                        "cart_id": str(existing.id),
                        "product_id": str(product.id),
                        "variant_id": str(variant.id),
                        "size": variant.size,
                        "color": variant.color,
                        "sku": variant.sku,
                        "quantity": existing.quantity,
                        "available_stock": available_stock
                    }
                }

            # ----------------------------------------------------
            # CREATE NEW CART ITEM
            # ----------------------------------------------------

            if quantity > available_stock:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Only {available_stock} item(s) "
                        "available for this variant"
                    )
                )

            cart_item = CartItem(
                user_id=user_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity
            )

            await CartRepository.create(
                db=db,
                cart_item=cart_item
            )

            return {
                "success": True,
                "status_code": 201,
                "message": "Product variant added to cart",
                "data": {
                    "cart_id": str(cart_item.id),
                    "product_id": str(product.id),
                    "variant_id": str(variant.id),
                    "size": variant.size,
                    "color": variant.color,
                    "sku": variant.sku,
                    "quantity": quantity,
                    "available_stock": available_stock
                }
            }

        except HTTPException:
            raise

        except SQLAlchemyError as e:

            raise HTTPException(
                status_code=500,
                detail="Database error while adding product to cart"
            )

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail="Something went wrong while adding product to cart"
            )

    # ============================================================
    # GET CART
    # ============================================================

    @staticmethod
    async def get_cart(
        db: AsyncSession,
        user_id: UUID,
        page: int,
        page_size: int
    ):

        items, total_records = (
            await CartRepository.get_cart_items(
                db=db,
                user_id=user_id,
                page=page,
                page_size=page_size
            )
        )

        # --------------------------------------------------------
        # EMPTY CART
        # --------------------------------------------------------

        if not items:

            return {
                "success": True,
                "status_code": 200,
                "message": "Cart is empty",
                "data": [],
                "cart_summary": {
                    "subtotal": 0,
                    "total_items": 0
                },
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_records": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                }
            }

        response_data = []

        subtotal = Decimal("0")

        total_quantity = 0

        # --------------------------------------------------------
        # PROCESS CART ITEMS
        # --------------------------------------------------------

        for item in items:

            product = item.product

            variant = item.variant

            # ----------------------------------------------------
            # VALIDATE VARIANT
            # ----------------------------------------------------

            if not variant:

                continue

            # ----------------------------------------------------
            # PRICE
            # ----------------------------------------------------

            mrp, sale_price = (
                CartService._get_variant_price(
                    product,
                    variant
                )
            )

            # ----------------------------------------------------
            # AVAILABLE STOCK
            # ----------------------------------------------------

            available_stock = max(
                0,
                variant.stock_qty - variant.reserved_qty
            )

            # ----------------------------------------------------
            # ITEM TOTAL
            # ----------------------------------------------------

            item_total = (
                Decimal(str(sale_price))
                *
                item.quantity
            )

            subtotal += item_total

            total_quantity += item.quantity

            # ----------------------------------------------------
            # RESPONSE
            # ----------------------------------------------------

            response_data.append({

                "cart_id": str(item.id),

                "product_id": str(product.id),

                "variant_id": str(variant.id),

                # -----------------------------------------------
                # CATEGORY
                # -----------------------------------------------

                "category_id": (
                    str(product.category_id)
                    if product.category_id
                    else None
                ),

                "category_name": (
                    product.category.name
                    if product.category
                    else None
                ),

                # -----------------------------------------------
                # PRODUCT
                # -----------------------------------------------

                "name": product.name,

                "slug": product.slug,

                "brand": product.brand,

                # -----------------------------------------------
                # VARIANT
                # -----------------------------------------------

                "size": variant.size,

                "color": variant.color,

                "sku": variant.sku,

                "attributes": variant.attributes,

                # -----------------------------------------------
                # PRICE
                # -----------------------------------------------

                "mrp": float(mrp),

                "sale_price": float(sale_price),

                # -----------------------------------------------
                # QUANTITY
                # -----------------------------------------------

                "quantity": item.quantity,

                "item_total": float(item_total),

                # -----------------------------------------------
                # STOCK
                # -----------------------------------------------

                "stock_qty": variant.stock_qty,

                "reserved_qty": variant.reserved_qty,

                "available_stock": available_stock,

                "stock_status": (
                    "Out of Stock"
                    if available_stock <= 0
                    else (
                        "Limited Stock"
                        if available_stock <= 10
                        else "In Stock"
                    )
                ),

                # -----------------------------------------------
                # IMAGE
                # -----------------------------------------------

                "thumbnail_url": (
                    product.thumbnail_url
                ),

                "images": [

                    {
                        "id": str(img.id),

                        "image_url": img.image_url,

                        "is_primary": img.is_primary,

                        "sort_order": img.sort_order

                    }

                    for img in product.images

                ]

            })

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return {

            "success": True,

            "status_code": 200,

            "message": "Cart fetched successfully",

            "data": response_data,

            "cart_summary": {

                "subtotal": float(subtotal),

                "total_items": total_quantity

            },

            "pagination": build_pagination(

                page=page,

                page_size=page_size,

                total_records=total_records

            )

        }

    # ============================================================
    # REMOVE FROM CART
    # ============================================================

    @staticmethod
    async def remove_from_cart(
        db: AsyncSession,
        user_id: UUID,
        product_id: UUID,
        variant_id: UUID
    ):

        try:

            item = (
                await CartRepository.get_by_user_and_variant(
                    db=db,
                    user_id=user_id,
                    product_id=product_id,
                    variant_id=variant_id
                )
            )

            if not item:

                raise HTTPException(
                    status_code=404,
                    detail="Product variant not found in cart"
                )

            await CartRepository.delete(
                db=db,
                cart_item=item
            )

            return {

                "success": True,

                "status_code": 200,

                "message": "Product variant removed from cart"

            }

        except HTTPException:
            raise

        except SQLAlchemyError:

            raise HTTPException(
                status_code=500,
                detail="Database error while removing product from cart"
            )

        except Exception:

            raise HTTPException(
                status_code=500,
                detail="Something went wrong while removing product from cart"
            )

    # ============================================================
    # GET CART SUMMARY
    # ============================================================

    @staticmethod
    async def get_cart_summary(
        db: AsyncSession,
        user_id: UUID
    ):

        cart_items = (
            await CartRepository.get_all_cart_items(
                db=db,
                user_id=user_id
            )
        )

        # --------------------------------------------------------
        # EMPTY CART
        # --------------------------------------------------------

        if not cart_items:

            return {

                "success": True,

                "status_code": 200,

                "message": "Cart is empty",

                "data": {

                    "total_items": 0,

                    "subtotal": 0,

                    "shipping_charge": 0,

                    "total_amount": 0,

                    "available_coupons": []

                }

            }

        subtotal = Decimal("0")

        total_quantity = 0

        # --------------------------------------------------------
        # CALCULATE SUBTOTAL
        # --------------------------------------------------------

        for item in cart_items:

            product = item.product

            variant = item.variant

            if not variant:

                continue

            # ----------------------------------------------------
            # PRICE
            # ----------------------------------------------------

            _, sale_price = (
                CartService._get_variant_price(
                    product,
                    variant
                )
            )

            # ----------------------------------------------------
            # STOCK VALIDATION
            # ----------------------------------------------------

            available_stock = max(
                0,
                variant.stock_qty - variant.reserved_qty
            )

            if available_stock < item.quantity:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient stock for "
                        f"{product.name}"
                        f" ({variant.size or ''}"
                        f"{' / ' if variant.size and variant.color else ''}"
                        f"{variant.color or ''})"
                    )
                )

            # ----------------------------------------------------
            # ITEM TOTAL
            # ----------------------------------------------------

            item_total = (
                Decimal(str(sale_price))
                *
                item.quantity
            )

            subtotal += item_total

            total_quantity += item.quantity

        # ========================================================
        # DELIVERY CHARGE
        # ========================================================

        shipping_charge = Decimal("0")

        settings = (
            await SettingRepository.get_settings(
                db
            )
        )

        if settings:

            delivery_charge = Decimal(
                str(
                    settings.delivery_charge or 0
                )
            )

            free_shipping_threshold = Decimal(
                str(
                    settings.free_shipping_threshold or 0
                )
            )

            if delivery_charge > 0:

                if (
                    free_shipping_threshold > 0
                    and
                    subtotal >= free_shipping_threshold
                ):

                    shipping_charge = Decimal("0")

                else:

                    shipping_charge = delivery_charge

        total_amount = (
            subtotal
            +
            shipping_charge
        )

        # ========================================================
        # COUPONS
        # ========================================================

        coupons = (
            await CouponRepository.get_active_coupons(
                db
            )
        )

        coupon_list = []

        for coupon in coupons:

            is_applicable = True

            reason = None

            discount_amount = Decimal("0")

            # ----------------------------------------------------
            # MINIMUM ORDER
            # ----------------------------------------------------

            if (
                subtotal
                <
                coupon.minimum_order_amount
            ):

                is_applicable = False

                reason = (
                    f"Minimum order amount "
                    f"{coupon.minimum_order_amount}"
                )

            # ----------------------------------------------------
            # USAGE LIMIT
            # ----------------------------------------------------

            if (
                coupon.usage_limit
                and
                coupon.used_count
                >=
                coupon.usage_limit
            ):

                is_applicable = False

                reason = (
                    "Coupon usage limit reached"
                )

            # ----------------------------------------------------
            # CALCULATE DISCOUNT
            # ----------------------------------------------------

            if is_applicable:

                # ----------------------------------------------
                # PERCENTAGE
                # ----------------------------------------------

                if (
                    coupon.coupon_type.value
                    ==
                    "percentage"
                ):

                    discount_amount = (
                        subtotal
                        *
                        coupon.discount_value
                    ) / Decimal("100")

                    if (
                        coupon.max_discount_amount
                        and
                        discount_amount
                        >
                        coupon.max_discount_amount
                    ):

                        discount_amount = (
                            coupon.max_discount_amount
                        )

                # ----------------------------------------------
                # FLAT
                # ----------------------------------------------

                elif (
                    coupon.coupon_type.value
                    ==
                    "flat"
                ):

                    discount_amount = (
                        coupon.discount_value
                    )

                    # Never discount more than
                    # the order amount.

                    discount_amount = min(
                        discount_amount,
                        total_amount
                    )

                # ----------------------------------------------
                # FREE SHIPPING
                # ----------------------------------------------

                elif (
                    coupon.coupon_type.value
                    ==
                    "free_shipping"
                ):

                    discount_amount = (
                        shipping_charge
                    )

            payable_amount = max(
                Decimal("0"),
                total_amount
                -
                discount_amount
            )

            coupon_list.append({

                "coupon_id": str(
                    coupon.id
                ),

                "coupon_code": (
                    coupon.code
                ),

                "coupon_title": (
                    coupon.title
                ),

                "is_applicable": (
                    is_applicable
                ),

                "reason": reason,

                "discount_amount": float(
                    discount_amount
                ),

                "payable_amount": float(
                    payable_amount
                )

            })

        # ========================================================
        # RESPONSE
        # ========================================================

        return {

            "success": True,

            "status_code": 200,

            "message": "Order summary fetched successfully",

            "data": {

                "total_items": total_quantity,

                "subtotal": float(
                    subtotal
                ),

                "shipping_charge": float(
                    shipping_charge
                ),

                "total_amount": float(
                    total_amount
                ),

                "available_coupons": coupon_list

            }

        }

    # ============================================================
    # APPLY COUPON
    # ============================================================

    @staticmethod
    async def apply_coupon(
        db: AsyncSession,
        user_id: UUID,
        coupon_code: str
    ):

        try:

            summary = (
                await CartService.get_cart_summary(
                    db=db,
                    user_id=user_id
                )
            )

            coupons = (
                summary["data"]
                ["available_coupons"]
            )

            selected_coupon = next(

                (
                    coupon

                    for coupon
                    in coupons

                    if coupon["coupon_code"]
                    ==
                    coupon_code
                ),

                None

            )

            if not selected_coupon:

                raise HTTPException(
                    status_code=404,
                    detail="Coupon not found"
                )

            if not selected_coupon[
                "is_applicable"
            ]:

                raise HTTPException(
                    status_code=400,
                    detail=selected_coupon[
                        "reason"
                    ]
                )

            return {

                "success": True,

                "status_code": 200,

                "message": "Coupon applied successfully",

                "data": {

                    "coupon_id": (
                        selected_coupon[
                            "coupon_id"
                        ]
                    ),

                    "coupon_code": (
                        selected_coupon[
                            "coupon_code"
                        ]
                    ),

                    "discount_amount": (
                        selected_coupon[
                            "discount_amount"
                        ]
                    ),

                    "payable_amount": (
                        selected_coupon[
                            "payable_amount"
                        ]
                    )

                }

            }

        except HTTPException:
            raise

        except SQLAlchemyError:

            raise HTTPException(
                status_code=500,
                detail="Database error while applying coupon"
            )

        except Exception:

            raise HTTPException(
                status_code=500,
                detail="Something went wrong while applying coupon"
            )

    # ============================================================
    # CLEAR CART
    # ============================================================

    @staticmethod
    async def clear_cart(
        db: AsyncSession,
        user_id: UUID
    ):

        try:

            await CartRepository.clear_cart(
                db=db,
                user_id=user_id
            )

            return {

                "success": True,

                "status_code": 200,

                "message": "Cart cleared successfully"

            }

        except SQLAlchemyError:

            raise HTTPException(
                status_code=500,
                detail="Database error while clearing cart"
            )

        except Exception:

            raise HTTPException(
                status_code=500,
                detail="Something went wrong while clearing cart"
            )