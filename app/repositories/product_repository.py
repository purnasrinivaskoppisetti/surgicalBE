from uuid import UUID

from sqlalchemy import (
    select,
    func,
    or_
)

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload

from app.models.models import (
    Product,
    ProductImage,
    Category,
    ProductStatus,
    Review,
    User
)


class ProductRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        product: Product
    ):

        db.add(product)

        await db.commit()
        await db.refresh(product)

        return product

    @staticmethod
    async def get_product_by_id(
        db: AsyncSession,
        product_id: UUID
    ):

        result = await db.execute(
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category),
                joinedload(Product.specifications),
                joinedload(Product.reviews)
                .joinedload(Review.user)
            )
            .where(
                Product.id == product_id,
                Product.is_deleted == False
            )
        )

        return result.unique().scalar_one_or_none()

    @staticmethod
    async def get_by_sku(
        db: AsyncSession,
        sku: str
    ):

        result = await db.execute(
            select(Product)
            .where(
                Product.sku == sku,
                Product.is_deleted == False
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slug(
        db: AsyncSession,
        slug: str
    ):

        result = await db.execute(
            select(Product)
            .where(
                Product.slug == slug,
                Product.is_deleted == False
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession
    ):

        result = await db.execute(
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category)
            )
            .where(
                Product.is_deleted == False
            )
            .order_by(
                Product.created_at.desc()
            )
        )

        return result.unique().scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        product: Product
    ):

        await db.commit()
        await db.refresh(product)

        return product

    @staticmethod
    async def delete(
        db: AsyncSession,
        product: Product
    ):

        product.is_deleted = True

        await db.commit()

        return True

    @staticmethod
    async def create_image(
        db: AsyncSession,
        image: ProductImage
    ):

        db.add(image)

        await db.commit()
        await db.refresh(image)

        return image

    @staticmethod
    async def create_images(
        db: AsyncSession,
        images: list[ProductImage]
    ):

        db.add_all(images)

        await db.commit()

        return images

    @staticmethod
    async def get_products(
        db: AsyncSession,
        page: int,
        page_size: int,
        search: str | None = None,
        category_id: UUID | None = None
    ):

        conditions = [
            Product.is_deleted == False,
            Product.status == ProductStatus.ACTIVE
        ]

        if category_id:
            conditions.append(
                Product.category_id == category_id
            )

        query = (
            select(Product)
            .join(
                Category,
                Product.category_id == Category.id,
                isouter=True
            )
            .options(
                joinedload(Product.images),
                joinedload(Product.category)
            )
            .where(*conditions)
        )

        if search:

            search_filter = or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%"),
                Product.short_description.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
                Product.hsn_code.ilike(f"%{search}%"),
                Category.name.ilike(f"%{search}%")
            )

            query = query.where(
                search_filter
            )

        count_query = (
            select(func.count(Product.id))
            .join(
                Category,
                Product.category_id == Category.id,
                isouter=True
            )
            .where(*conditions)
        )

        if search:
            count_query = count_query.where(
                search_filter
            )

        total_records = await db.scalar(
            count_query
        )

        result = await db.execute(
            query
            .order_by(
                Product.created_at.desc()
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(
                page_size
            )
        )

        products = (
            result.unique()
            .scalars()
            .all()
        )

        return (
            products,
            total_records
        )

    @staticmethod
    async def get_product_by_id(
        db: AsyncSession,
        product_id: UUID
    ):

        result = await db.execute(
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.specifications),
                joinedload(Product.category)
            )
            .where(
                Product.id == product_id,
                Product.is_deleted == False
            )
        )

        return result.unique().scalar_one_or_none()