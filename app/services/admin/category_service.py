from uuid import UUID

from fastapi import (
    HTTPException,
    status
)

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from slugify import slugify

from app.models.models import Category
from app.repositories.category_repository import (
    CategoryRepository
)


class CategoryService:

    @staticmethod
    async def create_category(
        db: AsyncSession,
        name: str,
        description: str | None,
        parent_id: UUID | None,
        is_active: bool
    ):

        try:

            slug = slugify(name)

            existing = await CategoryRepository.get_by_slug(
                db,
                slug
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category already exists"
                )

            if parent_id:

                parent = await CategoryRepository.get_by_id(
                    db,
                    parent_id
                )

                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent category not found"
                    )

            category = Category(
                name=name,
                slug=slug,
                description=description,
                parent_id=parent_id,
                is_active=is_active
            )

            return await CategoryRepository.create(
                db,
                category
            )

        except HTTPException:
            raise

        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def get_category(
        db: AsyncSession,
        category_id: UUID
    ):

        try:

            category = await CategoryRepository.get_by_id(
                db,
                category_id
            )

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )

            return category

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def get_categories(
        db: AsyncSession
    ):

        try:

            return await CategoryRepository.get_all(
                db
            )

        except Exception as e:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def update_category(
        db: AsyncSession,
        category_id: UUID,
        payload
    ):

        try:

            category = await CategoryRepository.get_by_id(
                db,
                category_id
            )

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )

            update_data = payload.model_dump(
                exclude_unset=True
            )

            if "name" in update_data:

                slug = slugify(
                    update_data["name"]
                )

                existing = await CategoryRepository.get_by_slug(
                    db,
                    slug
                )

                if (
                    existing and
                    existing.id != category.id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Category name already exists"
                    )

                category.name = update_data["name"]
                category.slug = slug

            if (
                "parent_id" in update_data and
                update_data["parent_id"]
            ):

                parent = await CategoryRepository.get_by_id(
                    db,
                    update_data["parent_id"]
                )

                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent category not found"
                    )

            for key, value in update_data.items():

                setattr(
                    category,
                    key,
                    value
                )

            return await CategoryRepository.update(
                db,
                category
            )

        except HTTPException:
            raise

        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def delete_category(
        db: AsyncSession,
        category_id: UUID
    ):

        try:

            category = await CategoryRepository.get_by_id(
                db,
                category_id
            )

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )

            await CategoryRepository.delete(
                db,
                category
            )

            return {
                "success": True,
                "message": "Category deleted successfully"
            }

        except HTTPException:
            raise

        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )