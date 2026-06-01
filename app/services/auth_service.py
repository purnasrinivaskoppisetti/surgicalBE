from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import User, UserRole
from app.repositories.user_repository import UserRepository

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)


class AuthService:

    def __init__(self):
        self.user_repo = UserRepository()

    async def register_admin(self, db, payload):

        try:

            existing = await self.user_repo.get_by_email(
                db,
                payload.email
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists"
                )

            user = User(
                full_name=payload.full_name,
                email=payload.email,
                phone=payload.phone,
                password_hash=hash_password(
                    payload.password
                ),
                role=UserRole.ADMIN
            )

            return await self.user_repo.create(
                db,
                user
            )

        except HTTPException:
            raise

        except SQLAlchemyError:
            raise HTTPException(
                status_code=500,
                detail="Database error"
            )

    async def register_user(self, db, payload):

        try:

            existing = await self.user_repo.get_by_email(
                db,
                payload.email
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists"
                )

            user = User(
                full_name=payload.full_name,
                email=payload.email,
                phone=payload.phone,
                password_hash=hash_password(
                    payload.password
                ),
                role=UserRole.CUSTOMER
            )

            return await self.user_repo.create(
                db,
                user
            )

        except HTTPException:
            raise

        except SQLAlchemyError:
            raise HTTPException(
                status_code=500,
                detail="Database error"
            )

    async def login(self, db, payload):

        try:

            user = await self.user_repo.get_by_email(
                db,
                payload.email
            )

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            if not verify_password(
                payload.password,
                user.password_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid password"
                )

            token = create_access_token(
                {
                    "sub": str(user.id),
                    "role": user.role.value,
                    "email": user.email
                }
            )

            return {
                "success": True,
                "status_code": 200,
                "message": "Login successful",
                "data": {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "id": str(user.id),
                        "full_name": user.full_name,
                        "email": user.email,
                        "phone": user.phone,
                        "role": user.role.value,
                        "created_at": user.created_at
                    }
                }
            }

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )