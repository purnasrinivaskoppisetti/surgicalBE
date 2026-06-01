from uuid import UUID

from fastapi import (
    HTTPException,
    UploadFile
)

from sqlalchemy.ext.asyncio import AsyncSession

from slugify import slugify

from app.models.models import (
    Product,
    ProductImage
)

from app.repositories.product_repository import (
    ProductRepository
)

from app.repositories.category_repository import (
    CategoryRepository
)

from app.repositories.product_image_repository import (
    ProductImageRepository
)

from app.storage.bluehost import (
    bluehost_storage
)


class ProductService:

    @staticmethod
    async def create_product(
        db: AsyncSession,
        payload,
        images: list[UploadFile]
    ):

        category = await CategoryRepository.get_by_id(
            db,
            payload.category_id
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        existing_sku = await ProductRepository.get_by_sku(
            db,
            payload.sku
        )

        if existing_sku:
            raise HTTPException(
                status_code=400,
                detail="SKU already exists"
            )

        if len(images) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one image required"
            )

        if len(images) > 6:
            raise HTTPException(
                status_code=400,
                detail="Maximum 6 images allowed"
            )

        slug = slugify(
            payload.name
        )

        product = Product(
            category_id=payload.category_id,

            name=payload.name,
            slug=slug,
            sku=payload.sku,

            brand=payload.brand,

            description=payload.description,
            short_description=payload.short_description,

            mrp=payload.mrp,
            sale_price=payload.sale_price,

            gst_percent=payload.gst_percent,

            stock_qty=payload.stock_qty,

            manufacturer=payload.manufacturer,
            hsn_code=payload.hsn_code,

            is_featured=payload.is_featured,
            is_bestseller=payload.is_bestseller,
            is_new_arrival=payload.is_new_arrival
        )

        product = await ProductRepository.create(
            db,
            product
        )

        uploaded_images = []

        thumbnail_url = None

        for index, image in enumerate(images):

            image_url = await bluehost_storage.upload_product_image(
                image
            )

            if index == 0:
                thumbnail_url = image_url

            uploaded_images.append(
                ProductImage(
                    product_id=product.id,
                    image_url=image_url,
                    is_primary=(index == 0),
                    sort_order=index
                )
            )

        await ProductImageRepository.bulk_create(
            db,
            uploaded_images
        )

        product.thumbnail_url = thumbnail_url

        await ProductRepository.update(
            db,
            product
        )

        return await ProductRepository.get_by_id(
            db,
            product.id
        )

    @staticmethod
    async def get_product(
        db: AsyncSession,
        product_id: UUID
    ):

        product = await ProductRepository.get_by_id(
            db,
            product_id
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        return product

    @staticmethod
    async def get_products(
        db: AsyncSession
    ):

        return await ProductRepository.get_all(
            db
        )

    @staticmethod
    async def update_product(
        db: AsyncSession,
        product_id: UUID,
        payload,
        images: list[UploadFile] | None = None
    ):

        product = await ProductRepository.get_by_id(
            db,
            product_id
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        update_data = payload.model_dump(
            exclude_unset=True
        )

        if "name" in update_data:

            product.name = update_data["name"]

            product.slug = slugify(
                update_data["name"]
            )

        for key, value in update_data.items():

            setattr(
                product,
                key,
                value
            )

        if images:

            if len(images) > 6:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 6 images allowed"
                )

            await ProductImageRepository.delete_product_images(
                db,
                product.id
            )

            image_records = []

            thumbnail_url = None

            for index, image in enumerate(images):

                image_url = await bluehost_storage.upload_product_image(
                    image
                )

                if index == 0:
                    thumbnail_url = image_url

                image_records.append(
                    ProductImage(
                        product_id=product.id,
                        image_url=image_url,
                        is_primary=(index == 0),
                        sort_order=index
                    )
                )

            await ProductImageRepository.bulk_create(
                db,
                image_records
            )

            product.thumbnail_url = thumbnail_url

        await ProductRepository.update(
            db,
            product
        )

        return await ProductRepository.get_by_id(
            db,
            product.id
        )

    @staticmethod
    async def delete_product(
        db: AsyncSession,
        product_id: UUID
    ):

        product = await ProductRepository.get_by_id(
            db,
            product_id
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        return await ProductRepository.delete(
            db,
            product
        )