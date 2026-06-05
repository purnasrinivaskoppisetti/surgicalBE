from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.category_repository import CategoryRepository

from app.repositories.product_repository import ProductRepository
from app.utils.pagination import build_pagination


class ProductService:

    @staticmethod
    async def get_products(
        db: AsyncSession,
        page: int,
        page_size: int,
        search: str | None = None,
        category_id: UUID | None = None
    ):

        products, total_records = await ProductRepository.get_products(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            category_id=category_id
        )

        response_data = []

        for product in products:

            discount_percentage = 0

            if float(product.mrp) > 0:
                discount_percentage = round(
                    (
                        (float(product.mrp) - float(product.sale_price))
                        / float(product.mrp)
                    ) * 100
                )

            # STOCK STATUS
            if product.stock_qty == 0:
                stock_status = "Out of Stock"
            elif product.stock_qty <= 10:
                stock_status = "Limited Stock"
            else:
                stock_status = "In Stock"

            response_data.append(
                                    {
                                        "id": str(product.id),

                                        "category_id": str(product.category_id)
                                        if product.category_id else None,

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
                                        "sku": product.sku,
                                        "brand": product.brand,
                                        "short_description": product.short_description,

                                        "mrp": str(product.mrp),
                                        "sale_price": str(product.sale_price),
                                        "discount_percentage": discount_percentage,

                                        "stock_qty": product.stock_qty,
                                        "stock_status": stock_status,

                                        "thumbnail_url": product.thumbnail_url,

                                        "rating": str(product.rating),
                                        "review_count": product.review_count,

                                        "is_featured": product.is_featured,
                                        "is_bestseller": product.is_bestseller,
                                        "is_new_arrival": product.is_new_arrival,

                                        "created_at": product.created_at,

                                        "images": [
                                            {
                                                "id": str(img.id),
                                                "image_url": img.image_url,
                                                "is_primary": img.is_primary,
                                                "sort_order": img.sort_order
                                            }
                                            for img in product.images
                                        ]
                                    }
                                )

        return {
            "success": True,
            "status_code": 200,
            "message": "Products fetched successfully",
            "data": response_data,
            "pagination": build_pagination(
                page=page,
                page_size=page_size,
                total_records=total_records
            )
        }

    @staticmethod
    async def get_product_details(
        db: AsyncSession,
        product_id: UUID
    ):

        product = await ProductRepository.get_product_by_id(
            db=db,
            product_id=product_id
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        discount_percentage = 0

        if float(product.mrp) > 0:
            discount_percentage = round(
                (
                    (float(product.mrp) - float(product.sale_price))
                    / float(product.mrp)
                ) * 100
            )

        if product.stock_qty == 0:
            stock_status = "Out of Stock"
        elif product.stock_qty <= 10:
            stock_status = "Limited Stock"
        else:
            stock_status = "In Stock"

        approved_reviews = [
            review
            for review in product.reviews
            if review.status.value == "approved"
        ]

        return {
            "success": True,
            "status_code": 200,
            "message": "Product details fetched successfully",
            "data": {
                "id": str(product.id),

                "category": {
                    "id": str(product.category.id)
                    if product.category else None,

                    "name": product.category.name
                    if product.category else None,

                    "slug": product.category.slug
                    if product.category else None
                },

                "name": product.name,
                "slug": product.slug,
                "sku": product.sku,
                "brand": product.brand,

                "description": product.description,
                "short_description": product.short_description,

                "mrp": str(product.mrp),
                "sale_price": str(product.sale_price),
                "discount_percentage": discount_percentage,

                "stock_qty": product.stock_qty,
                "stock_status": stock_status,

                "thumbnail_url": product.thumbnail_url,

                "manufacturer": product.manufacturer,
                "hsn_code": product.hsn_code,

                "status": product.status.value,

                "rating": str(product.rating),
                "review_count": product.review_count,

                "is_featured": product.is_featured,
                "is_bestseller": product.is_bestseller,
                "is_new_arrival": product.is_new_arrival,

                "images": [
                    {
                        "id": str(img.id),
                        "image_url": img.image_url,
                        "is_primary": img.is_primary,
                        "sort_order": img.sort_order
                    }
                    for img in product.images
                ],

                "specifications": [
                    {
                        "id": str(spec.id),
                        "spec_key": spec.spec_key,
                        "spec_value": spec.spec_value
                    }
                    for spec in product.specifications
                ],

                "reviews": [
                    {
                        "id": str(review.id),

                        "user": {
                            "id": str(review.user.id),
                            "name": review.user.full_name
                        },

                        "rating": review.rating,

                        "review_text": review.review_text,

                        "image_url": review.image_url,

                        "is_verified_purchase":
                            review.is_verified_purchase,

                        "created_at":
                            review.created_at
                    }
                    for review in approved_reviews
                ],

                "created_at": product.created_at,
                "updated_at": product.updated_at
            }
        }