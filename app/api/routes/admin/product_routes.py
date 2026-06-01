from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    status
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin

from app.schemas.admin.product_schema import (
    ProductCreate,
    ProductUpdate,
    ProductResponse
)

from app.schemas.admin.common_schema import ApiResponse

from app.services.admin.product_service import ProductService

router = APIRouter(
    prefix="/admin/products",
    tags=["Admin Products"]
)


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_product(
    category_id: UUID = Form(...),
    name: str = Form(...),
    sku: str = Form(...),
    brand: str | None = Form(None),
    description: str | None = Form(None),
    short_description: str | None = Form(None),
    mrp: float = Form(...),
    sale_price: float = Form(...),
    gst_percent: float = Form(18),
    stock_qty: int = Form(0),
    manufacturer: str | None = Form(None),
    hsn_code: str | None = Form(None),
    is_featured: bool = Form(False),
    is_bestseller: bool = Form(False),
    is_new_arrival: bool = Form(False),
    images: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    payload = ProductCreate(
        category_id=category_id,
        name=name,
        sku=sku,
        brand=brand,
        description=description,
        short_description=short_description,
        mrp=mrp,
        sale_price=sale_price,
        gst_percent=gst_percent,
        stock_qty=stock_qty,
        manufacturer=manufacturer,
        hsn_code=hsn_code,
        is_featured=is_featured,
        is_bestseller=is_bestseller,
        is_new_arrival=is_new_arrival
    )

    product = await ProductService.create_product(
        db,
        payload,
        images
    )

    return ApiResponse(
        success=True,
        status_code=201,
        message="Product created successfully",
        data=ProductResponse.model_validate(product)
    )


@router.get(
    "",
    response_model=ApiResponse
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    products = await ProductService.get_products(db)

    return ApiResponse(
        success=True,
        status_code=200,
        message="Products fetched successfully",
        data=[
            ProductResponse.model_validate(product)
            for product in products
        ]
    )


@router.get(
    "/{product_id}",
    response_model=ApiResponse
)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    product = await ProductService.get_product(
        db,
        product_id
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Product fetched successfully",
        data=ProductResponse.model_validate(product)
    )


@router.put(
    "/{product_id}",
    response_model=ApiResponse
)
async def update_product(
    product_id: UUID,
    category_id: UUID | None = Form(None),
    name: str | None = Form(None),
    sku: str | None = Form(None),
    brand: str | None = Form(None),
    description: str | None = Form(None),
    short_description: str | None = Form(None),
    mrp: float | None = Form(None),
    sale_price: float | None = Form(None),
    gst_percent: float | None = Form(None),
    stock_qty: int | None = Form(None),
    manufacturer: str | None = Form(None),
    hsn_code: str | None = Form(None),
    is_featured: bool | None = Form(None),
    is_bestseller: bool | None = Form(None),
    is_new_arrival: bool | None = Form(None),
    images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    payload = ProductUpdate(
        category_id=category_id,
        name=name,
        sku=sku,
        brand=brand,
        description=description,
        short_description=short_description,
        mrp=mrp,
        sale_price=sale_price,
        gst_percent=gst_percent,
        stock_qty=stock_qty,
        manufacturer=manufacturer,
        hsn_code=hsn_code,
        is_featured=is_featured,
        is_bestseller=is_bestseller,
        is_new_arrival=is_new_arrival
    )

    product = await ProductService.update_product(
        db,
        product_id,
        payload,
        images
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Product updated successfully",
        data=ProductResponse.model_validate(product)
    )


@router.delete(
    "/{product_id}",
    response_model=ApiResponse
)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    await ProductService.delete_product(
        db,
        product_id
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Product deleted successfully",
        data=None
    )