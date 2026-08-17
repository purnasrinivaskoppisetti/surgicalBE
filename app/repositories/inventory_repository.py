from datetime import datetime

from sqlalchemy import select, func, desc

from app.models.models import (
    Product,
    ProductVariant,
    InventoryLog,
)


class InventoryRepository:

    @staticmethod
    async def get_inventory_dashboard(db):

        # ============================================================
        # TOTAL STOCK
        # ============================================================

        total_stock = await db.scalar(
            select(
                func.coalesce(
                    func.sum(ProductVariant.stock_qty),
                    0
                )
            )
            .join(
                Product,
                Product.id == ProductVariant.product_id
            )
            .where(
                Product.is_deleted == False,
                ProductVariant.is_active == True,
            )
        )

        # ============================================================
        # LOW STOCK
        #
        # 1 - 25 units
        # ============================================================

        low_stock = await db.scalar(
            select(
                func.count(ProductVariant.id)
            )
            .join(
                Product,
                Product.id == ProductVariant.product_id
            )
            .where(
                Product.is_deleted == False,
                ProductVariant.is_active == True,
                ProductVariant.stock_qty.between(1, 25),
            )
        )

        # ============================================================
        # OUT OF STOCK
        # ============================================================

        out_of_stock = await db.scalar(
            select(
                func.count(ProductVariant.id)
            )
            .join(
                Product,
                Product.id == ProductVariant.product_id
            )
            .where(
                Product.is_deleted == False,
                ProductVariant.is_active == True,
                ProductVariant.stock_qty == 0,
            )
        )

        # ============================================================
        # STOCK MOVEMENTS TODAY
        # ============================================================

        today = datetime.utcnow().date()

        movements_today = await db.scalar(
            select(
                func.count(InventoryLog.id)
            )
            .where(
                func.date(
                    InventoryLog.created_at
                ) == today
            )
        )

        # ============================================================
        # INVENTORY PRODUCTS / VARIANTS
        #
        # Inventory belongs to ProductVariant, not Product.
        # ============================================================

        result = await db.execute(
            select(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                ProductVariant.id.label("variant_id"),
                ProductVariant.sku.label("sku"),
                ProductVariant.size.label("size"),
                ProductVariant.color.label("color"),
                ProductVariant.stock_qty.label("stock_qty"),
                ProductVariant.reserved_qty.label("reserved_qty"),
            )
            .join(
                ProductVariant,
                ProductVariant.product_id == Product.id
            )
            .where(
                Product.is_deleted == False,
                ProductVariant.is_active == True,
            )
            .order_by(
                ProductVariant.stock_qty.asc(),
                Product.name.asc(),
            )
        )

        products = result.all()

        return (
            int(total_stock or 0),
            int(low_stock or 0),
            int(out_of_stock or 0),
            int(movements_today or 0),
            products,
        )