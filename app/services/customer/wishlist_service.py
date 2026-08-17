from uuid import UUID

from app.models.models import WishlistItem

from app.repositories.wishlist_repository import (
    WishlistRepository
)

from app.repositories.product_repository import (
    ProductRepository
)


class WishlistService:

    # ============================================================
    # ADD TO WISHLIST
    # ============================================================

    @staticmethod
    async def add_to_wishlist(
        db,
        user_id: UUID,
        product_id: UUID
    ):

        product = await ProductRepository.get_by_id(
            db,
            product_id
        )

        if not product:

            return {
                "success": False,
                "status_code": 404,
                "message": "Product not found"
            }

        existing = (
            await WishlistRepository.get_by_user_and_product(
                db,
                user_id,
                product_id
            )
        )

        if existing:

            return {
                "success": False,
                "status_code": 400,
                "message": "Product already in wishlist"
            }

        wishlist_item = WishlistItem(
            user_id=user_id,
            product_id=product_id
        )

        await WishlistRepository.create(
            db,
            wishlist_item
        )

        return {
            "success": True,
            "status_code": 201,
            "message": "Product added to wishlist"
        }

    # ============================================================
    # GET CUSTOMER WISHLIST
    # ============================================================

    @staticmethod
    async def get_wishlist(
        db,
        user_id: UUID,
        page: int,
        page_size: int
    ):

        items, total_records = (
            await WishlistRepository.get_user_wishlist(
                db=db,
                user_id=user_id,
                page=page,
                page_size=page_size
            )
        )

        # ========================================================
        # PAGINATION
        # ========================================================

        total_pages = (
            (total_records + page_size - 1) // page_size
            if total_records > 0
            else 0
        )

        # ========================================================
        # EMPTY WISHLIST
        # ========================================================

        if not items:

            return {
                "success": True,
                "status_code": 200,
                "message": "Your wishlist is empty",
                "data": [],
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_records": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                }
            }

        wishlist_data = []

        # ========================================================
        # BUILD WISHLIST RESPONSE
        # ========================================================

        for item in items:

            product = item.product

            if not product:
                continue

            # ====================================================
            # DISCOUNT
            # ====================================================

            discount_percentage = 0

            if product.mrp is not None and float(product.mrp) > 0:

                discount_percentage = round(
                    (
                        (
                            float(product.mrp)
                            -
                            float(product.sale_price)
                        )
                        /
                        float(product.mrp)
                    )
                    * 100
                )

            # ====================================================
            # AVAILABLE STOCK
            #
            # Stock is maintained at ProductVariant level.
            #
            # available stock =
            # stock_qty - reserved_qty
            # ====================================================

            available_stock = sum(
                max(
                    0,
                    variant.stock_qty - variant.reserved_qty
                )
                for variant in product.variants
            )

            # ====================================================
            # STOCK STATUS
            # ====================================================

            if available_stock == 0:

                stock_status = "Out of Stock"

            elif available_stock <= 10:

                stock_status = "Limited Stock"

            else:

                stock_status = "In Stock"

            # ====================================================
            # VARIANTS
            # ====================================================

            variants_data = []

            for variant in product.variants:

                variant_available_stock = max(
                    0,
                    variant.stock_qty - variant.reserved_qty
                )

                variant_mrp = (
                    variant.mrp
                    if variant.mrp is not None
                    else product.mrp
                )

                variant_sale_price = (
                    variant.sale_price
                    if variant.sale_price is not None
                    else product.sale_price
                )

                variants_data.append(
                    {
                        "variant_id": str(
                            variant.id
                        ),

                        "sku": variant.sku,

                        "size": variant.size,

                        "color": variant.color,

                        "attributes": (
                            variant.attributes
                        ),

                        "mrp": str(
                            variant_mrp
                        ),

                        "sale_price": str(
                            variant_sale_price
                        ),

                        "stock_qty": (
                            variant.stock_qty
                        ),

                        "reserved_qty": (
                            variant.reserved_qty
                        ),

                        "available_stock": (
                            variant_available_stock
                        ),

                        "is_active": (
                            variant.is_active
                        )
                    }
                )

            # ====================================================
            # PRODUCT DATA
            # ====================================================

            wishlist_data.append(
                {
                    "wishlist_id": str(
                        item.id
                    ),

                    "product_id": str(
                        product.id
                    ),

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

                    "name": product.name,

                    "slug": product.slug,

                    # Product can have multiple SKUs
                    "skus": [
                        variant.sku
                        for variant in product.variants
                    ],

                    "brand": product.brand,

                    "short_description": (
                        product.short_description
                    ),

                    "mrp": str(
                        product.mrp
                    ),

                    "sale_price": str(
                        product.sale_price
                    ),

                    "discount_percentage": (
                        discount_percentage
                    ),

                    "stock_qty": (
                        available_stock
                    ),

                    "stock_status": (
                        stock_status
                    ),

                    "thumbnail_url": (
                        product.thumbnail_url
                    ),

                    "rating": str(
                        product.rating
                    ),

                    "review_count": (
                        product.review_count
                    ),

                    "is_featured": (
                        product.is_featured
                    ),

                    "is_bestseller": (
                        product.is_bestseller
                    ),

                    "is_new_arrival": (
                        product.is_new_arrival
                    ),

                    "created_at": (
                        product.created_at
                    ),

                    # =================================================
                    # VARIANTS
                    # =================================================

                    "variants": variants_data,

                    # =================================================
                    # IMAGES
                    # =================================================

                    "images": [
                        {
                            "id": str(
                                image.id
                            ),

                            "image_url": (
                                image.image_url
                            ),

                            "is_primary": (
                                image.is_primary
                            ),

                            "sort_order": (
                                image.sort_order
                            )
                        }

                        for image in product.images
                    ]
                }
            )

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return {
            "success": True,
            "status_code": 200,
            "message": "Wishlist fetched successfully",
            "data": wishlist_data,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": (
                    page < total_pages
                ),
                "has_previous": (
                    page > 1
                )
            }
        }

    # ============================================================
    # REMOVE FROM WISHLIST
    # ============================================================

    @staticmethod
    async def remove_from_wishlist(
        db,
        user_id: UUID,
        product_id: UUID
    ):

        item = (
            await WishlistRepository.get_by_user_and_product(
                db,
                user_id,
                product_id
            )
        )

        if not item:

            return {
                "success": False,
                "status_code": 404,
                "message": "Product not found in wishlist"
            }

        await WishlistRepository.delete(
            db,
            item
        )

        return {
            "success": True,
            "status_code": 200,
            "message": "Product removed from wishlist"
        }