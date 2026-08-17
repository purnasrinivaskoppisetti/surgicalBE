from app.repositories.inventory_repository import (
    InventoryRepository
)


class InventoryService:

    @staticmethod
    async def get_inventory_dashboard(db):

        (
            total_stock,
            low_stock,
            out_of_stock,
            movements_today,
            products
        ) = await InventoryRepository.get_inventory_dashboard(
            db
        )

        inventory_products = []

        for product in products:

            stock_qty = int(
                product.stock_qty or 0
            )

            reserved_qty = int(
                product.reserved_qty or 0
            )

            # --------------------------------------------------------
            # AVAILABLE STOCK
            # --------------------------------------------------------

            available_stock = max(
                stock_qty - reserved_qty,
                0
            )

            # --------------------------------------------------------
            # STOCK STATUS
            # --------------------------------------------------------

            if stock_qty == 0:
                status = "out_of_stock"

            elif stock_qty <= 25:
                status = "low"

            else:
                status = "healthy"

            # --------------------------------------------------------
            # STOCK PERCENTAGE
            #
            # UI representation:
            # 0   -> 0%
            # 50  -> 50%
            # 100 -> 100%
            # 150 -> 100%
            #
            # Maximum displayed percentage is 100.
            # --------------------------------------------------------

            stock_percentage = min(
                stock_qty,
                100
            )

            inventory_products.append({
                "product_id": str(
                    product.product_id
                ),

                "variant_id": str(
                    product.variant_id
                ),

                "product_name": product.product_name,

                "sku": product.sku,

                "size": product.size,

                "color": product.color,

                "stock_qty": stock_qty,

                "reserved_qty": reserved_qty,

                "available_stock": available_stock,

                "status": status,

                "stock_percentage": stock_percentage,
            })

        return {
            "summary": {
                "units_in_stock": total_stock,

                "low_stock": low_stock,

                "out_of_stock": out_of_stock,

                "stock_movements_today": movements_today,
            },

            "products": inventory_products,
        }