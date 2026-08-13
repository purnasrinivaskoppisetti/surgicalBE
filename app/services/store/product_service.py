from uuid import UUID
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product_repository import ProductRepository
from app.utils.pagination import build_pagination


class ProductService:

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

        If variant does not have its own price,
        use the product-level price.

        Example:

        Product sale_price = 999

        S -> None      => 999
        M -> None      => 999
        L -> 1049      => 1049
        XL -> 1099     => 1099
        """

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

        return (
            variant_mrp,
            variant_sale_price
        )

    # ============================================================
    # HELPER - DISCOUNT
    # ============================================================

    @staticmethod
    
    def _calculate_discount(
        mrp,
        sale_price
    ):
        if not mrp or float(mrp) <= 0:
            return 0

        if sale_price is None:
            return 0

        discount = (
            (
                float(mrp) - float(sale_price)
            )
            / float(mrp)
        ) * 100

        return round(discount)

    # ============================================================
    # HELPER - STOCK STATUS
    # ============================================================

    @staticmethod
    def _get_stock_status(
        stock_qty: int
    ):

        if stock_qty <= 0:
            return "Out of Stock"

        elif stock_qty <= 10:
            return "Limited Stock"

        return "In Stock"

    # ============================================================
    # HELPER - VARIANT RESPONSE
    # ============================================================

    @staticmethod
    def _build_variant_response(
        product,
        variant
    ):

        mrp, sale_price = (
            ProductService._get_variant_price(
                product,
                variant
            )
        )

        discount_percentage = (
            ProductService._calculate_discount(
                mrp,
                sale_price
            )
        )

        available_stock = max(
            0,
            variant.stock_qty - variant.reserved_qty
        )

        return {
            "id": str(variant.id),

            "size": variant.size,

            "color": variant.color,

            "sku": variant.sku,

            "mrp": str(mrp),

            "sale_price": str(sale_price),

            "discount_percentage": (
                discount_percentage
            ),

            "stock_qty": variant.stock_qty,

            "reserved_qty": variant.reserved_qty,

            "available_stock": available_stock,

            "stock_status": (
                ProductService._get_stock_status(
                    available_stock
                )
            ),

            "attributes": variant.attributes,

            "is_active": variant.is_active,

            "created_at": variant.created_at,

            "updated_at": variant.updated_at,
        }

    # ============================================================
    # HELPER - GET TOTAL STOCK
    # ============================================================

    @staticmethod
    def _get_total_stock(
        product
    ):

        total_stock = 0

        for variant in product.variants:

            if not variant.is_active:
                continue

            available_stock = max(
                0,
                variant.stock_qty
                -
                variant.reserved_qty
            )

            total_stock += available_stock

        return total_stock

    # ============================================================
    # GET ALL PRODUCTS
    # ============================================================

    @staticmethod
    async def get_products(

        db: AsyncSession,

        page: int,

        page_size: int,

        search: str | None = None,

        category_id: UUID | None = None

    ):

        products, total_records = (
            await ProductRepository.get_products(

                db=db,

                page=page,

                page_size=page_size,

                search=search,

                category_id=category_id

            )
        )

        response_data = []

        for product in products:

            # ----------------------------------------------------
            # TOTAL STOCK FROM VARIANTS
            # ----------------------------------------------------

            total_stock = (
                ProductService._get_total_stock(
                    product
                )
            )

            stock_status = (
                ProductService._get_stock_status(
                    total_stock
                )
            )

            # ----------------------------------------------------
            # PRODUCT BASE PRICE
            # ----------------------------------------------------

            product_mrp = product.mrp

            product_sale_price = (
                product.sale_price
            )

            discount_percentage = (
                ProductService._calculate_discount(
                    product_mrp,
                    product_sale_price
                )
            )

            # ----------------------------------------------------
            # APPROVED REVIEWS
            # ----------------------------------------------------

            approved_reviews = [

                review

                for review in product.reviews

                if review.status.value
                == "approved"

            ]

            review_count = len(
                approved_reviews
            )

            average_rating = (

                round(

                    sum(
                        review.rating
                        for review
                        in approved_reviews
                    )
                    /
                    review_count,

                    1

                )

                if review_count > 0

                else 0

            )

            # ----------------------------------------------------
            # VARIANTS
            # ----------------------------------------------------

            variants = [

                ProductService._build_variant_response(

                    product,

                    variant

                )

                for variant in product.variants

                if variant.is_active

            ]

            # ----------------------------------------------------
            # RESPONSE
            # ----------------------------------------------------

            response_data.append({

                "id": str(
                    product.id
                ),

                "category_id": (

                    str(
                        product.category_id
                    )

                    if product.category_id

                    else None

                ),

                "category_name": (

                    product.category.name

                    if product.category

                    else None

                ),

                "category_slug": (

                    product.category.slug

                    if product.category

                    else None

                ),

                "name": product.name,

                "slug": product.slug,

                "brand": product.brand,

                "short_description": (
                    product.short_description
                ),

                # ------------------------------------------------
                # PRODUCT BASE PRICE
                # ------------------------------------------------

                "mrp": str(
                    product_mrp
                ),

                "sale_price": str(
                    product_sale_price
                ),

                "discount_percentage": (
                    discount_percentage
                ),

                # ------------------------------------------------
                # TOTAL STOCK
                # ------------------------------------------------

                "stock_qty": total_stock,

                "stock_status": stock_status,

                # ------------------------------------------------
                # VARIANTS
                # ------------------------------------------------

                "variants": variants,

                # ------------------------------------------------
                # SHIPPING DIMENSIONS
                # ------------------------------------------------

                "weight": float(
                    product.weight or 0
                ),

                "length": float(
                    product.length or 0
                ),

                "breadth": float(
                    product.breadth or 0
                ),

                "height": float(
                    product.height or 0
                ),

                # ------------------------------------------------
                # IMAGE
                # ------------------------------------------------

                "thumbnail_url": (
                    product.thumbnail_url
                ),

                # ------------------------------------------------
                # RATING
                # ------------------------------------------------

                "rating": average_rating,

                "review_count": review_count,

                # ------------------------------------------------
                # FLAGS
                # ------------------------------------------------

                "is_featured": (
                    product.is_featured
                ),

                "is_bestseller": (
                    product.is_bestseller
                ),

                "is_new_arrival": (
                    product.is_new_arrival
                ),

                # ------------------------------------------------
                # IMAGES
                # ------------------------------------------------

                "images": [

                    {
                        "id": str(
                            img.id
                        ),

                        "image_url": (
                            img.image_url
                        ),

                        "is_primary": (
                            img.is_primary
                        ),

                        "sort_order": (
                            img.sort_order
                        )
                    }

                    for img in product.images

                ],

                "created_at": (
                    product.created_at
                )

            })

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return {

            "success": True,

            "status_code": 200,

            "message": (
                "Products fetched successfully"
            ),

            "data": response_data,

            "pagination": build_pagination(

                page=page,

                page_size=page_size,

                total_records=total_records

            )

        }

    # ============================================================
    # GET PRODUCT DETAILS
    # ============================================================

    @staticmethod
    async def get_product_details(

        db: AsyncSession,

        product_id: UUID

    ):

        product = await (
            ProductRepository.get_by_id(

                db=db,

                product_id=product_id

            )
        )

        if not product:

            raise HTTPException(

                status_code=404,

                detail="Product not found"

            )

        # ========================================================
        # TOTAL STOCK
        # ========================================================

        total_stock = (
            ProductService._get_total_stock(
                product
            )
        )

        stock_status = (
            ProductService._get_stock_status(
                total_stock
            )
        )

        # ========================================================
        # PRODUCT PRICE
        # ========================================================

        discount_percentage = (
            ProductService._calculate_discount(

                product.mrp,

                product.sale_price

            )
        )

        # ========================================================
        # REVIEWS
        # ========================================================

        approved_reviews = [

            review

            for review in product.reviews

            if review.status.value
            == "approved"

        ]

        review_count = len(
            approved_reviews
        )

        average_rating = (

            round(

                sum(
                    review.rating
                    for review
                    in approved_reviews
                )
                /
                review_count,

                1

            )

            if review_count > 0

            else 0

        )

        # ========================================================
        # RATING BREAKDOWN
        # ========================================================

        rating_breakdown = {

            "5_star": 0,

            "4_star": 0,

            "3_star": 0,

            "2_star": 0,

            "1_star": 0

        }

        for review in approved_reviews:

            rating = int(
                review.rating
            )

            key = f"{rating}_star"

            if key in rating_breakdown:

                rating_breakdown[key] += 1

        # ========================================================
        # VARIANTS
        # ========================================================

        variants = [

            ProductService._build_variant_response(

                product,

                variant

            )

            for variant in product.variants

            if variant.is_active

        ]

        # ========================================================
        # RESPONSE
        # ========================================================

        return {

            "success": True,

            "status_code": 200,

            "message": (
                "Product details fetched successfully"
            ),

            "data": {

                # ==================================================
                # BASIC PRODUCT
                # ==================================================

                "id": str(
                    product.id
                ),

                "category": {

                    "id": (

                        str(
                            product.category.id
                        )

                        if product.category

                        else None

                    ),

                    "name": (

                        product.category.name

                        if product.category

                        else None

                    ),

                    "slug": (

                        product.category.slug

                        if product.category

                        else None

                    )

                },

                "name": product.name,

                "slug": product.slug,

                "brand": product.brand,

                "description": (
                    product.description
                ),

                "short_description": (
                    product.short_description
                ),

                # ==================================================
                # PRODUCT PRICE
                # ==================================================

                "mrp": str(
                    product.mrp
                ),

                "sale_price": str(
                    product.sale_price
                ),

                "discount_percentage": (
                    discount_percentage
                ),

                # ==================================================
                # TOTAL STOCK
                # ==================================================

                "stock_qty": total_stock,

                "stock_status": (
                    stock_status
                ),

                # ==================================================
                # VARIANTS
                # ==================================================

                "variants": variants,

                # ==================================================
                # SHIPPING
                # ==================================================

                "weight": float(
                    product.weight or 0
                ),

                "length": float(
                    product.length or 0
                ),

                "breadth": float(
                    product.breadth or 0
                ),

                "height": float(
                    product.height or 0
                ),

                # ==================================================
                # OTHER INFORMATION
                # ==================================================

                "thumbnail_url": (
                    product.thumbnail_url
                ),

                "manufacturer": (
                    product.manufacturer
                ),

                "hsn_code": (
                    product.hsn_code
                ),

                "status": (
                    product.status.value
                ),

                # ==================================================
                # RATING
                # ==================================================

                "rating": average_rating,

                "review_count": review_count,

                "rating_summary": {

                    "average_rating": (
                        average_rating
                    ),

                    "total_reviews": (
                        review_count
                    ),

                    "five_star": (
                        rating_breakdown[
                            "5_star"
                        ]
                    ),

                    "four_star": (
                        rating_breakdown[
                            "4_star"
                        ]
                    ),

                    "three_star": (
                        rating_breakdown[
                            "3_star"
                        ]
                    ),

                    "two_star": (
                        rating_breakdown[
                            "2_star"
                        ]
                    ),

                    "one_star": (
                        rating_breakdown[
                            "1_star"
                        ]
                    )

                },

                # ==================================================
                # FLAGS
                # ==================================================

                "is_featured": (
                    product.is_featured
                ),

                "is_bestseller": (
                    product.is_bestseller
                ),

                "is_new_arrival": (
                    product.is_new_arrival
                ),

                # ==================================================
                # IMAGES
                # ==================================================

                "images": [

                    {

                        "id": str(
                            img.id
                        ),

                        "image_url": (
                            img.image_url
                        ),

                        "is_primary": (
                            img.is_primary
                        ),

                        "sort_order": (
                            img.sort_order
                        )

                    }

                    for img in product.images

                ],

                # ==================================================
                # SPECIFICATIONS
                # ==================================================

                "specifications": [

                    {

                        "id": str(
                            spec.id
                        ),

                        "spec_key": (
                            spec.spec_key
                        ),

                        "spec_value": (
                            spec.spec_value
                        )

                    }

                    for spec
                    in product.specifications

                ],

                # ==================================================
                # REVIEWS
                # ==================================================

                "reviews": [

                    {

                        "id": str(
                            review.id
                        ),

                        "user": {

                            "id": str(
                                review.user.id
                            ),

                            "name": (
                                review.user.full_name
                            )

                        },

                        "rating": (
                            review.rating
                        ),

                        "review_text": (
                            review.review_text
                        ),

                        "image_url": (
                            review.image_url
                        ),

                        "is_verified_purchase": (
                            review.is_verified_purchase
                        ),

                        "created_at": (
                            review.created_at
                        )

                    }

                    for review
                    in approved_reviews

                ],

                # ==================================================
                # DATES
                # ==================================================

                "created_at": (
                    product.created_at
                ),

                "updated_at": (
                    product.updated_at
                )

            }

        }