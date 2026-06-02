from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.category_repository import CategoryRepository


class CategoryService:

    @staticmethod
    async def get_categories(
        db: AsyncSession
    ):

        categories = await CategoryRepository.get_all(db)

        return {
            "success": True,
            "status_code": 200,
            "message": "Categories fetched successfully",
            "data": [
                {
                    "id": str(category.id),
                    "name": category.name,
                    "icon":category.icon,
                    "slug": category.slug
                }
                for category in categories
            ]
        }