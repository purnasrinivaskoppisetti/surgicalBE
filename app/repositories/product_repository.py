from uuid import UUID

from sqlalchemy import (
    select,
    func,
    or_,
)

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import (
    joinedload,
    selectinload,
)

from app.models.models import (
    Product,
    ProductVariant,
    ProductImage,
    Category,
    ProductStatus,
    Review,
    ReviewStatus,
)


class ProductRepository:

    # ============================================================
    # CREATE PRODUCT
    # ============================================================

    @staticmethod
    async def create(
        db: AsyncSession,
        product: Product
    ):
        """
        Create a product.

        We use flush() instead of commit() here because
        variants and images are also created as part of the
        same transaction.

        The service will commit everything together.
        """

        db.add(product)

        await db.flush()

        return product

    # ============================================================
    # GET PRODUCT BY ID
    # ============================================================

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        product_id: UUID
    ):
        """
        Get one product with:

        - Category
        - Images
        - Variants
        - Reviews
        - Specifications
        - Review users
        """

        result = await db.execute(

            select(Product)

            .options(

                # ------------------------------------------------
                # CATEGORY
                # ------------------------------------------------

                joinedload(
                    Product.category
                ),

                # ------------------------------------------------
                # IMAGES
                # ------------------------------------------------

                selectinload(
                    Product.images
                ),

                # ------------------------------------------------
                # VARIANTS
                # ------------------------------------------------

                selectinload(
                    Product.variants
                ),

                # ------------------------------------------------
                # REVIEWS
                # ------------------------------------------------

                selectinload(
                    Product.reviews
                ).joinedload(
                    Review.user
                ),

                # ------------------------------------------------
                # SPECIFICATIONS
                # ------------------------------------------------

                selectinload(
                    Product.specifications
                ),
            )

            .where(

                Product.id == product_id,

                Product.is_deleted == False,

                Product.status == ProductStatus.ACTIVE,

            )
        )

        return result.unique().scalar_one_or_none()

    # ============================================================
    # GET PRODUCT BY VARIANT SKU
    # ============================================================

    @staticmethod
    async def get_by_sku(
        db: AsyncSession,
        sku: str
    ):
        """
        SKU belongs to ProductVariant.

        Example:

        TS-RED-S-001
        TS-RED-M-001
        TS-RED-L-001

        Returns the matching ProductVariant.
        """

        result = await db.execute(

            select(ProductVariant)

            .options(

                joinedload(
                    ProductVariant.product
                )

            )

            .where(

                ProductVariant.sku == sku,

                ProductVariant.is_active == True,

                ProductVariant.product.has(
                    Product.is_deleted == False
                )

            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # GET VARIANT BY ID
    # ============================================================

    @staticmethod
    async def get_variant_by_id(
        db: AsyncSession,
        variant_id: UUID
    ):
        """
        Get a single product variant.
        """

        result = await db.execute(

            select(ProductVariant)

            .options(

                joinedload(
                    ProductVariant.product
                )

            )

            .where(

                ProductVariant.id == variant_id,

                ProductVariant.is_active == True,

            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # GET PRODUCT + VARIANT
    # ============================================================

    @staticmethod
    async def get_product_variant(
        db: AsyncSession,
        product_id: UUID,
        variant_id: UUID
    ):
        """
        Get a variant belonging to a particular product.
        """

        result = await db.execute(

            select(ProductVariant)

            .where(

                ProductVariant.id == variant_id,

                ProductVariant.product_id == product_id,

                ProductVariant.is_active == True,

            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # GET PRODUCT BY SLUG
    # ============================================================

    @staticmethod
    async def get_by_slug(
        db: AsyncSession,
        slug: str
    ):

        result = await db.execute(

            select(Product)

            .options(

                joinedload(
                    Product.category
                ),

                selectinload(
                    Product.images
                ),

                selectinload(
                    Product.variants
                ),

                selectinload(
                    Product.reviews
                ).joinedload(
                    Review.user
                ),

                selectinload(
                    Product.specifications
                ),

            )

            .where(

                Product.slug == slug,

                Product.is_deleted == False,

                Product.status == ProductStatus.ACTIVE,

            )
        )

        return result.unique().scalar_one_or_none()

    # ============================================================
    # GET ALL PRODUCTS
    # ============================================================

    @staticmethod
    async def get_all(
        db: AsyncSession
    ):

        result = await db.execute(

            select(Product)

            .options(

                joinedload(
                    Product.category
                ),

                selectinload(
                    Product.images
                ),

                selectinload(
                    Product.variants
                ),

                selectinload(
                    Product.reviews
                ),

            )

            .where(
                Product.is_deleted == False
            )

            .order_by(
                Product.created_at.desc()
            )
        )

        return (
            result
            .unique()
            .scalars()
            .all()
        )

    # ============================================================
    # UPDATE PRODUCT
    # ============================================================

    @staticmethod
    async def update(
        db: AsyncSession,
        product: Product
    ):

        await db.commit()

        await db.refresh(
            product
        )

        return product

    # ============================================================
    # DELETE PRODUCT
    # ============================================================

    @staticmethod
    async def delete(
        db: AsyncSession,
        product: Product
    ):

        product.is_deleted = True

        await db.commit()

        return True

    # ============================================================
    # GET PRODUCTS - PAGINATION
    # ============================================================

    @staticmethod
    async def get_products(

        db: AsyncSession,

        page: int,

        page_size: int,

        search: str | None = None,

        category_id: UUID | None = None,

    ):

        # --------------------------------------------------------
        # BASE CONDITIONS
        # --------------------------------------------------------

        conditions = [

            Product.is_deleted == False,

            Product.status == ProductStatus.ACTIVE,

        ]

        # --------------------------------------------------------
        # CATEGORY FILTER
        # --------------------------------------------------------

        if category_id:

            conditions.append(

                Product.category_id
                ==
                category_id

            )

        # --------------------------------------------------------
        # MAIN QUERY
        # --------------------------------------------------------

        query = (

            select(Product)

            .join(

                Category,

                Product.category_id
                ==
                Category.id,

                isouter=True

            )

            .options(

                joinedload(
                    Product.category
                ),

                selectinload(
                    Product.images
                ),

                selectinload(
                    Product.variants
                ),

                selectinload(
                    Product.reviews
                ),

            )

            .where(
                *conditions
            )
        )

        # --------------------------------------------------------
        # SEARCH
        # --------------------------------------------------------

        if search:

            search_filter = or_(

                # Product name
                Product.name.ilike(
                    f"%{search}%"
                ),

                # Brand
                Product.brand.ilike(
                    f"%{search}%"
                ),

                # Short description
                Product.short_description.ilike(
                    f"%{search}%"
                ),

                # Description
                Product.description.ilike(
                    f"%{search}%"
                ),

                # HSN
                Product.hsn_code.ilike(
                    f"%{search}%"
                ),

                # Category
                Category.name.ilike(
                    f"%{search}%"
                ),

                # Variant SKU
                Product.variants.any(

                    ProductVariant.sku.ilike(
                        f"%{search}%"
                    )

                ),

                # Variant size
                Product.variants.any(

                    ProductVariant.size.ilike(
                        f"%{search}%"
                    )

                ),

                # Variant color
                Product.variants.any(

                    ProductVariant.color.ilike(
                        f"%{search}%"
                    )

                ),

            )

            query = query.where(
                search_filter
            )

        # --------------------------------------------------------
        # COUNT QUERY
        # --------------------------------------------------------

        count_query = (

            select(
                func.count(
                    Product.id
                )
            )

            .join(

                Category,

                Product.category_id
                ==
                Category.id,

                isouter=True

            )

            .where(
                *conditions
            )
        )

        if search:

            count_query = count_query.where(
                search_filter
            )

        total_records = await db.scalar(
            count_query
        )

        total_records = (
            total_records or 0
        )

        # --------------------------------------------------------
        # PAGINATION QUERY
        # --------------------------------------------------------

        result = await db.execute(

            query

            .order_by(

                Product.created_at.desc()

            )

            .offset(

                (page - 1)
                *
                page_size

            )

            .limit(
                page_size
            )
        )

        products = (

            result

            .unique()

            .scalars()

            .all()

        )

        return (
            products,
            total_records
        )

    # ============================================================
    # GET ACTIVE VARIANTS FOR PRODUCT
    # ============================================================

    @staticmethod
    async def get_variants(
        db: AsyncSession,
        product_id: UUID
    ):

        result = await db.execute(

            select(ProductVariant)

            .where(

                ProductVariant.product_id
                ==
                product_id,

                ProductVariant.is_active
                ==
                True,

            )

            .order_by(
                ProductVariant.created_at.asc()
            )
        )

        return (
            result
            .scalars()
            .all()
        )

    # ============================================================
    # GET VARIANTS BY SIZE
    # ============================================================

    @staticmethod
    async def get_variants_by_size(

        db: AsyncSession,

        product_id: UUID,

        size: str

    ):

        result = await db.execute(

            select(ProductVariant)

            .where(

                ProductVariant.product_id
                ==
                product_id,

                ProductVariant.size
                ==
                size,

                ProductVariant.is_active
                ==
                True,

            )
        )

        return (
            result
            .scalars()
            .all()
        )

    # ============================================================
    # GET VARIANTS BY COLOR
    # ============================================================

    @staticmethod
    async def get_variants_by_color(

        db: AsyncSession,

        product_id: UUID,

        color: str

    ):

        result = await db.execute(

            select(ProductVariant)

            .where(

                ProductVariant.product_id
                ==
                product_id,

                ProductVariant.color
                ==
                color,

                ProductVariant.is_active
                ==
                True,

            )
        )

        return (
            result
            .scalars()
            .all()
        )

    # ============================================================
    # CHECK VARIANT STOCK
    # ============================================================

    @staticmethod
    async def check_variant_stock(

        db: AsyncSession,

        variant_id: UUID,

        quantity: int

    ):

        result = await db.execute(

            select(ProductVariant)

            .where(

                ProductVariant.id
                ==
                variant_id,

                ProductVariant.is_active
                ==
                True,

            )

        )

        variant = result.scalar_one_or_none()

        if not variant:
            return False

        available_qty = (

            variant.stock_qty
            -
            variant.reserved_qty

        )

        return available_qty >= quantity

    # ============================================================
    # GET VARIANT FOR UPDATE
    # ============================================================

    @staticmethod
    async def get_variant_for_update(

        db: AsyncSession,

        variant_id: UUID

    ):

        """
        IMPORTANT FOR CHECKOUT.

        SELECT ... FOR UPDATE locks the variant row.

        This prevents two customers from buying the
        last available item at the same time.
        """

        result = await db.execute(

            select(ProductVariant)

            .where(

                ProductVariant.id
                ==
                variant_id,

                ProductVariant.is_active
                ==
                True,

            )

            .with_for_update()

        )

        return result.scalar_one_or_none()

    # ============================================================
    # RESERVE STOCK
    # ============================================================

    @staticmethod
    async def reserve_stock(

        db: AsyncSession,

        variant_id: UUID,

        quantity: int

    ):

        """
        Reserve stock during checkout/payment process.

        available =
            stock_qty - reserved_qty
        """

        variant = await (
            ProductRepository.get_variant_for_update(
                db,
                variant_id
            )
        )

        if not variant:

            return None

        available_qty = (

            variant.stock_qty
            -
            variant.reserved_qty

        )

        if available_qty < quantity:

            return None

        variant.reserved_qty += quantity

        await db.flush()

        return variant

    # ============================================================
    # RELEASE RESERVED STOCK
    # ============================================================

    @staticmethod
    async def release_reserved_stock(

        db: AsyncSession,

        variant_id: UUID,

        quantity: int

    ):

        variant = await (
            ProductRepository.get_variant_for_update(
                db,
                variant_id
            )
        )

        if not variant:
            return None

        variant.reserved_qty = max(

            0,

            variant.reserved_qty
            -
            quantity

        )

        await db.flush()

        return variant

    # ============================================================
    # DECREASE STOCK AFTER SUCCESSFUL PAYMENT
    # ============================================================

    @staticmethod
    async def decrease_stock(

        db: AsyncSession,

        variant_id: UUID,

        quantity: int

    ):

        """
        Call this ONLY after payment is successfully confirmed.

        Example:

            Size M
            Stock = 20
            Customer buys = 3

            Stock becomes = 17
        """

        variant = await (
            ProductRepository.get_variant_for_update(
                db,
                variant_id
            )
        )

        if not variant:

            return None

        available_qty = (

            variant.stock_qty
            -
            variant.reserved_qty

        )

        if available_qty < quantity:

            raise ValueError(
                "Insufficient stock"
            )

        variant.stock_qty -= quantity

        # Remove reservation
        variant.reserved_qty = max(

            0,

            variant.reserved_qty
            -
            quantity

        )

        await db.flush()

        return variant

    # ============================================================
    # INCREASE STOCK
    # ============================================================

    @staticmethod
    async def increase_stock(

        db: AsyncSession,

        variant_id: UUID,

        quantity: int

    ):

        variant = await (
            ProductRepository.get_variant_for_update(
                db,
                variant_id
            )
        )

        if not variant:

            return None

        variant.stock_qty += quantity

        await db.flush()

        return variant

    # ============================================================
    # UPDATE PRODUCT RATING
    # ============================================================

    @staticmethod
    async def update_product_rating(

        db: AsyncSession,

        product_id: UUID

    ):

        result = await db.execute(

            select(

                func.avg(
                    Review.rating
                ),

                func.count(
                    Review.id
                )

            )

            .where(

                Review.product_id
                ==
                product_id,

                Review.status
                ==
                ReviewStatus.APPROVED,

            )

        )

        avg_rating, review_count = (
            result.one()
        )

        product = await (
            ProductRepository.get_by_id(
                db,
                product_id
            )
        )

        if not product:
            return None

        product.rating = float(

            round(

                avg_rating or 0,

                1

            )

        )

        product.review_count = (
            review_count or 0
        )

        await db.commit()

        await db.refresh(
            product
        )

        return product