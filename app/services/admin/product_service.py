from uuid import UUID

from fastapi import (
    HTTPException,
    UploadFile,
)

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError

from slugify import slugify

from app.models.models import (
    Product,
    ProductVariant,
    ProductImage,
)

from app.core.storage import local_storage

from app.repositories.product_repository import (
    ProductRepository,
)

from app.repositories.category_repository import (
    CategoryRepository,
)

from app.repositories.product_image_repository import (
    ProductImageRepository,
)


class ProductService:

    # ========================================================
    # STOCK STATUS
    # ========================================================

    @staticmethod
    def get_stock_status(
        stock_qty: int
    ):

        if stock_qty <= 0:
            return "Out of Stock"

        if stock_qty <= 10:
            return "Limited Stock"

        return "In Stock"

    # ========================================================
    # DISCOUNT
    # ========================================================

    @staticmethod
    def calculate_discount(
        mrp,
        sale_price
    ):

        if float(mrp) <= 0:
            return 0

        return round(
            (
                (
                    float(mrp)
                    -
                    float(sale_price)
                )
                /
                float(mrp)
            )
            * 100
        )

    # ========================================================
    # CREATE PRODUCT
    # ========================================================

    @staticmethod
    async def create_product(

        db: AsyncSession,

        payload,

        images: list[UploadFile]

    ):

        try:

            # ------------------------------------------------
            # CATEGORY
            # ------------------------------------------------

            category = await CategoryRepository.get_by_id(
                db,
                payload.category_id
            )

            if not category:

                raise HTTPException(
                    status_code=404,
                    detail="Category not found"
                )

            # ------------------------------------------------
            # PRICE VALIDATION
            # ------------------------------------------------

            if payload.sale_price > payload.mrp:

                raise HTTPException(
                    status_code=400,
                    detail="Sale price cannot be greater than MRP"
                )

            # ------------------------------------------------
            # IMAGE VALIDATION
            # ------------------------------------------------

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

            MAX_IMAGE_SIZE = 3 * 1024 * 1024

            for image in images:

                if image.content_type not in [

                    "image/jpeg",

                    "image/jpg",

                    "image/png",

                    "image/webp",

                    "image/jfif",

                ]:

                    raise HTTPException(

                        status_code=400,

                        detail=(
                            f"{image.filename} "
                            "is not a valid image"
                        )
                    )

                contents = await image.read()

                if len(contents) > MAX_IMAGE_SIZE:

                    raise HTTPException(

                        status_code=400,

                        detail=(
                            f"{image.filename} "
                            "exceeds 3 MB limit"
                        )
                    )

                await image.seek(0)

            # ------------------------------------------------
            # VALIDATE VARIANTS
            # ------------------------------------------------

            if not payload.variants:

                raise HTTPException(
                    status_code=400,
                    detail="At least one product variant is required"
                )

            variant_skus = set()

            for variant in payload.variants:

                # --------------------------------------------
                # DUPLICATE SKU IN REQUEST
                # --------------------------------------------

                if variant.sku in variant_skus:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Duplicate SKU in variants: "
                            f"{variant.sku}"
                        )
                    )

                variant_skus.add(
                    variant.sku
                )

                # --------------------------------------------
                # CHECK DATABASE SKU
                # --------------------------------------------

                existing_sku = (
                    await ProductRepository.get_by_sku(
                        db,
                        variant.sku
                    )
                )

                if existing_sku:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"SKU already exists: "
                            f"{variant.sku}"
                        )
                    )

                # --------------------------------------------
                # VARIANT PRICE
                # --------------------------------------------

                variant_mrp = (
                    variant.mrp
                    if variant.mrp is not None
                    else payload.mrp
                )

                variant_sale_price = (
                    variant.sale_price
                    if variant.sale_price is not None
                    else payload.sale_price
                )

                if variant_sale_price > variant_mrp:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Sale price cannot be greater "
                            f"than MRP for SKU {variant.sku}"
                        )
                    )

            # ------------------------------------------------
            # SLUG
            # ------------------------------------------------

            slug = slugify(
                payload.name
            )

            # ------------------------------------------------
            # CREATE PRODUCT
            # ------------------------------------------------

            product = Product(

                category_id=payload.category_id,

                name=payload.name,

                slug=slug,

                brand=payload.brand,

                description=payload.description,

                short_description=payload.short_description,

                mrp=payload.mrp,

                sale_price=payload.sale_price,

                weight=payload.weight,

                length=payload.length,

                breadth=payload.breadth,

                height=payload.height,

                manufacturer=payload.manufacturer,

                hsn_code=payload.hsn_code,

                is_featured=payload.is_featured,

                is_bestseller=payload.is_bestseller,

                is_new_arrival=payload.is_new_arrival,

            )

            product = await ProductRepository.create(
                db,
                product
            )

            # ------------------------------------------------
            # CREATE VARIANTS
            # ------------------------------------------------

            created_variants = []

            for variant in payload.variants:

                variant_mrp = (
                    variant.mrp
                    if variant.mrp is not None
                    else payload.mrp
                )

                variant_sale_price = (
                    variant.sale_price
                    if variant.sale_price is not None
                    else payload.sale_price
                )

                product_variant = ProductVariant(

                    product_id=product.id,

                    size=variant.size,

                    color=variant.color,

                    sku=variant.sku,

                    mrp=variant_mrp,

                    sale_price=variant_sale_price,

                    stock_qty=variant.stock_qty,

                    reserved_qty=0,

                    attributes=variant.attributes,

                    is_active=True,

                )

                db.add(
                    product_variant
                )

                created_variants.append(
                    product_variant
                )

            # ------------------------------------------------
            # FLUSH VARIANTS
            # ------------------------------------------------

            await db.flush()

            # ------------------------------------------------
            # UPLOAD IMAGES
            # ------------------------------------------------

            image_records = []

            thumbnail_url = None

            for index, image in enumerate(images):

                image_url = (
                    await local_storage.upload_product_image(
                        image
                    )
                )

                if index == 0:

                    thumbnail_url = image_url

                image_records.append(

                    ProductImage(

                        product_id=product.id,

                        image_url=image_url,

                        is_primary=(index == 0),

                        sort_order=index,

                    )
                )

            await ProductImageRepository.bulk_create(
                db,
                image_records
            )

            # ------------------------------------------------
            # THUMBNAIL
            # ------------------------------------------------

            product.thumbnail_url = thumbnail_url

            # ------------------------------------------------
            # COMMIT EVERYTHING
            # ------------------------------------------------

            await db.commit()

            await db.refresh(
                product
            )

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            return {

                "success": True,

                "status_code": 201,

                "message": "Product created successfully",

                "data": {

                    "id": str(
                        product.id
                    ),

                    "name": product.name,

                    "variants": [

                        {

                            "id": str(
                                variant.id
                            ),

                            "size": variant.size,

                            "color": variant.color,

                            "sku": variant.sku,

                            "mrp": str(
                                variant.mrp
                            ),

                            "sale_price": str(
                                variant.sale_price
                            ),

                            "stock_qty": variant.stock_qty,

                        }

                        for variant in created_variants

                    ]

                }
            }

        except HTTPException:

            await db.rollback()

            raise

        except IntegrityError:

            await db.rollback()

            raise HTTPException(

                status_code=400,

                detail="Duplicate product or variant data found"

            )

        except Exception as e:

            await db.rollback()

            raise HTTPException(

                status_code=500,

                detail=(
                    f"Failed to create product: {str(e)}"
                )

            )

    # ========================================================
    # GET PRODUCTS
    # ========================================================

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

        total_pages = (

            (
                total_records
                +
                page_size
                -
                1
            )
            //
            page_size

            if total_records

            else 0

        )

        data = []

        for product in products:

            # ------------------------------------------------
            # TOTAL STOCK FROM VARIANTS
            # ------------------------------------------------

            total_stock = sum(

                (
                    variant.stock_qty
                    -
                    variant.reserved_qty
                )

                for variant in product.variants

                if variant.is_active

            )

            stock_status = (
                ProductService.get_stock_status(
                    total_stock
                )
            )

            discount_percentage = (

                ProductService.calculate_discount(

                    product.mrp,

                    product.sale_price

                )
            )

            data.append({

                "id": str(
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

                "discount_percentage":
                    discount_percentage,

                "stock_qty":
                    total_stock,

                "stock_status":
                    stock_status,

                "weight":
                    float(
                        product.weight or 0
                    ),

                "length":
                    float(
                        product.length or 0
                    ),

                "breadth":
                    float(
                        product.breadth or 0
                    ),

                "height":
                    float(
                        product.height or 0
                    ),

                "thumbnail_url":
                    product.thumbnail_url,

                "rating":
                    float(
                        product.rating or 0
                    ),

                "review_count":
                    product.review_count or 0,

                "is_featured":
                    product.is_featured,

                "is_bestseller":
                    product.is_bestseller,

                "is_new_arrival":
                    product.is_new_arrival,

                "created_at":
                    product.created_at,

                # ------------------------------------------------
                # VARIANTS
                # ------------------------------------------------

                "variants": [

                    {

                        "id":
                            str(variant.id),

                        "size":
                            variant.size,

                        "color":
                            variant.color,

                        "sku":
                            variant.sku,

                        "mrp":
                            str(variant.mrp),

                        "sale_price":
                            str(variant.sale_price),

                        "stock_qty":
                            variant.stock_qty,

                        "reserved_qty":
                            variant.reserved_qty,

                        "available_qty":
                            max(
                                0,
                                variant.stock_qty
                                -
                                variant.reserved_qty
                            ),

                        "stock_status":
                            ProductService.get_stock_status(
                                max(
                                    0,
                                    variant.stock_qty
                                    -
                                    variant.reserved_qty
                                )
                            ),

                        "attributes":
                            variant.attributes,

                        "is_active":
                            variant.is_active,

                    }

                    for variant
                    in product.variants

                ],

                "images": [

                    {

                        "id":
                            str(img.id),

                        "image_url":
                            img.image_url,

                        "is_primary":
                            img.is_primary,

                        "sort_order":
                            img.sort_order

                    }

                    for img in product.images

                ]

            })

        return {

            "success": True,

            "status_code": 200,

            "message":
                "Products fetched successfully",

            "filters": {

                "search":
                    search,

                "category_id":
                    (
                        str(category_id)
                        if category_id
                        else None
                    )

            },

            "data":
                data,

            "pagination": {

                "current_page":
                    page,

                "page_size":
                    page_size,

                "total_records":
                    total_records,

                "total_pages":
                    total_pages,

                "has_next":
                    page < total_pages,

                "has_previous":
                    page > 1

            }

        }

    # ========================================================
    # GET PRODUCT
    # ========================================================

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

        total_stock = sum(

            (
                variant.stock_qty
                -
                variant.reserved_qty
            )

            for variant in product.variants

            if variant.is_active

        )

        return {

            "success": True,

            "status_code": 200,

            "message":
                "Product fetched successfully",

            "data": {

                "id":
                    str(product.id),

                "category_id":
                    (
                        str(product.category_id)
                        if product.category_id
                        else None
                    ),

                "category_name":
                    (
                        product.category.name
                        if product.category
                        else None
                    ),

                "name":
                    product.name,

                "slug":
                    product.slug,

                "brand":
                    product.brand,

                "description":
                    product.description,

                "short_description":
                    product.short_description,

                "mrp":
                    str(product.mrp),

                "sale_price":
                    str(product.sale_price),

                "discount_percentage":
                    ProductService.calculate_discount(
                        product.mrp,
                        product.sale_price
                    ),

                "stock_qty":
                    total_stock,

                "stock_status":
                    ProductService.get_stock_status(
                        total_stock
                    ),

                "weight":
                    float(product.weight or 0),

                "length":
                    float(product.length or 0),

                "breadth":
                    float(product.breadth or 0),

                "height":
                    float(product.height or 0),

                "thumbnail_url":
                    product.thumbnail_url,

                "manufacturer":
                    product.manufacturer,

                "hsn_code":
                    product.hsn_code,

                "rating":
                    float(product.rating or 0),

                "review_count":
                    product.review_count or 0,

                "is_featured":
                    product.is_featured,

                "is_bestseller":
                    product.is_bestseller,

                "is_new_arrival":
                    product.is_new_arrival,

                # ------------------------------------------------
                # VARIANTS
                # ------------------------------------------------

                "variants": [

                    {

                        "id":
                            str(variant.id),

                        "size":
                            variant.size,

                        "color":
                            variant.color,

                        "sku":
                            variant.sku,

                        "mrp":
                            str(variant.mrp),

                        "sale_price":
                            str(variant.sale_price),

                        "stock_qty":
                            variant.stock_qty,

                        "reserved_qty":
                            variant.reserved_qty,

                        "available_qty":
                            max(
                                0,
                                variant.stock_qty
                                -
                                variant.reserved_qty
                            ),

                        "stock_status":
                            ProductService.get_stock_status(
                                max(
                                    0,
                                    variant.stock_qty
                                    -
                                    variant.reserved_qty
                                )
                            ),

                        "attributes":
                            variant.attributes,

                        "is_active":
                            variant.is_active,

                    }

                    for variant
                    in product.variants

                ],

                "created_at":
                    product.created_at,

                "images": [

                    {

                        "id":
                            str(img.id),

                        "image_url":
                            img.image_url,

                        "is_primary":
                            img.is_primary,

                        "sort_order":
                            img.sort_order

                    }

                    for img in product.images

                ]

            }

        }

    # ========================================================
    # UPDATE PRODUCT
    # ========================================================

    @staticmethod
    async def update_product(

        db: AsyncSession,

        product_id: UUID,

        payload,

        images: list[UploadFile] | None = None

    ):

        try:

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

            # ------------------------------------------------
            # VARIANTS
            # ------------------------------------------------

            variants_data = update_data.pop(
                "variants",
                None
            )

            # ------------------------------------------------
            # PRICE
            # ------------------------------------------------

            new_mrp = update_data.get(
                "mrp",
                product.mrp
            )

            new_sale_price = update_data.get(
                "sale_price",
                product.sale_price
            )

            if new_sale_price > new_mrp:

                raise HTTPException(
                    status_code=400,
                    detail="Sale price cannot be greater than MRP"
                )

            # ------------------------------------------------
            # NAME / SLUG
            # ------------------------------------------------

            if "name" in update_data:

                product.name = update_data["name"]

                product.slug = slugify(
                    update_data["name"]
                )

            # ------------------------------------------------
            # PRODUCT FIELDS
            # ------------------------------------------------

            for key, value in update_data.items():

                setattr(
                    product,
                    key,
                    value
                )

            # ------------------------------------------------
            # UPDATE VARIANTS
            # ------------------------------------------------

            if variants_data is not None:

                existing_variants = {
                    variant.id: variant
                    for variant in product.variants
                }

                incoming_ids = set()

                for variant_data in variants_data:

                    variant_id = variant_data.get(
                        "id"
                    )

                    # ----------------------------------------
                    # EXISTING VARIANT
                    # ----------------------------------------

                    if variant_id:

                        variant_id = UUID(
                            str(variant_id)
                        )

                        variant = existing_variants.get(
                            variant_id
                        )

                        if not variant:

                            raise HTTPException(
                                status_code=404,
                                detail=(
                                    f"Variant not found: "
                                    f"{variant_id}"
                                )
                            )

                        incoming_ids.add(
                            variant_id
                        )

                        for key, value in variant_data.items():

                            if key == "id":
                                continue

                            if value is not None:

                                setattr(
                                    variant,
                                    key,
                                    value
                                )

                    # ----------------------------------------
                    # NEW VARIANT
                    # ----------------------------------------

                    else:

                        sku = variant_data.get(
                            "sku"
                        )

                        if not sku:

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    "SKU is required "
                                    "for new variant"
                                )
                            )

                        existing_sku = (
                            await ProductRepository.get_by_sku(
                                db,
                                sku
                            )
                        )

                        if existing_sku:

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"SKU already exists: "
                                    f"{sku}"
                                )
                            )

                        variant_mrp = (
                            variant_data.get(
                                "mrp"
                            )
                            or product.mrp
                        )

                        variant_sale_price = (
                            variant_data.get(
                                "sale_price"
                            )
                            or product.sale_price
                        )

                        if variant_sale_price > variant_mrp:

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"Sale price cannot be "
                                    f"greater than MRP for "
                                    f"SKU {sku}"
                                )
                            )

                        new_variant = ProductVariant(

                            product_id=product.id,

                            size=variant_data.get(
                                "size"
                            ),

                            color=variant_data.get(
                                "color"
                            ),

                            sku=sku,

                            mrp=variant_mrp,

                            sale_price=variant_sale_price,

                            stock_qty=variant_data.get(
                                "stock_qty",
                                0
                            ),

                            reserved_qty=0,

                            attributes=variant_data.get(
                                "attributes"
                            ),

                            is_active=variant_data.get(
                                "is_active",
                                True
                            ),

                        )

                        db.add(
                            new_variant
                        )

                # ------------------------------------------------
                # DELETE REMOVED VARIANTS
                # ------------------------------------------------
                #
                # IMPORTANT:
                # Don't automatically delete variants that have
                # existing orders.
                #
                # Instead mark them inactive.
                #

                for variant_id, variant in existing_variants.items():

                    if variant_id not in incoming_ids:

                        variant.is_active = False

            # ------------------------------------------------
            # IMAGES
            # ------------------------------------------------

            if images:

                if len(images) > 6:

                    raise HTTPException(
                        status_code=400,
                        detail="Maximum 6 images allowed"
                    )

                MAX_IMAGE_SIZE = 3 * 1024 * 1024

                for image in images:

                    if image.content_type not in [

                        "image/jpeg",
                        "image/jpg",
                        "image/png",
                        "image/webp",
                        "image/jfif",

                    ]:

                        raise HTTPException(

                            status_code=400,

                            detail=(
                                f"{image.filename} "
                                "is not a valid image"
                            )
                        )

                    contents = await image.read()

                    if len(contents) > MAX_IMAGE_SIZE:

                        raise HTTPException(

                            status_code=400,

                            detail=(
                                f"{image.filename} "
                                "exceeds 3 MB limit"
                            )
                        )

                    await image.seek(0)

                await ProductImageRepository.delete_product_images(
                    db,
                    product.id
                )

                image_records = []

                thumbnail_url = None

                for index, image in enumerate(images):

                    image_url = (
                        await local_storage.upload_product_image(
                            image
                        )
                    )

                    if index == 0:

                        thumbnail_url = image_url

                    image_records.append(

                        ProductImage(

                            product_id=product.id,

                            image_url=image_url,

                            is_primary=(index == 0),

                            sort_order=index,

                        )
                    )

                await ProductImageRepository.bulk_create(
                    db,
                    image_records
                )

                product.thumbnail_url = thumbnail_url

            # ------------------------------------------------
            # COMMIT
            # ------------------------------------------------

            await db.commit()

            return {

                "success": True,

                "status_code": 200,

                "message":
                    "Product updated successfully"

            }

        except HTTPException:

            await db.rollback()

            raise

        except IntegrityError:

            await db.rollback()

            raise HTTPException(

                status_code=400,

                detail="Duplicate product or variant data found"

            )

        except Exception as e:

            await db.rollback()

            raise HTTPException(

                status_code=500,

                detail=(
                    f"Failed to update product: {str(e)}"
                )

            )

    # ========================================================
    # DELETE PRODUCT
    # ========================================================

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

        await ProductRepository.delete(
            db,
            product
        )

        return {

            "success": True,

            "status_code": 200,

            "message":
                "Product deleted successfully"

        }