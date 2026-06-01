from sqlalchemy import select

from app.models.models import User


class UserRepository:

    async def get_by_email(
        self,
        db,
        email: str
    ):

        result = await db.execute(
            select(User).where(
                User.email == email
            )
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        db,
        user
    ):

        db.add(user)

        await db.commit()

        await db.refresh(user)

        return user