from sqlalchemy import select

from app.models.models import StoreSetting


class SettingRepository:

    @staticmethod
    async def get_settings(db):

        result = await db.execute(
            select(StoreSetting)
            .limit(1)
        )

        return result.scalar_one_or_none()