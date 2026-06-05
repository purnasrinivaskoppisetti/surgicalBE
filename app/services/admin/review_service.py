from fastapi import HTTPException

from app.models.models import (
    ReviewStatus
)

from app.repositories.review_repository import (
    ReviewRepository
)


class AdminReviewService:

    @staticmethod
    async def get_reviews(
        db,
        status=None
    ):

        reviews = await ReviewRepository.get_all_reviews(
            db=db,
            status=status
        )

        return {
            "success": True,
            "status_code": 200,
            "data": [
                {
                    "id": str(review.id),

                    "product_id": str(review.product.id),
                    "product_name": review.product.name,

                    "user_id": str(review.user.id),
                    "user_name": review.user.full_name,

                    "rating": review.rating,
                    "review_text": review.review_text,

                    "image_url": review.image_url,

                    "verified_purchase":
                        review.is_verified_purchase,

                    "status":
                        review.status.value,

                    "admin_note":
                        review.admin_note,

                    "created_at":
                        review.created_at
                }
                for review in reviews
            ]
        }

    @staticmethod
    async def approve_review(
        db,
        review_id,
        admin_note
    ):

        review = await ReviewRepository.get_by_id(
            db,
            review_id
        )

        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found"
            )

        review.status = ReviewStatus.APPROVED
        review.admin_note = admin_note

        await ReviewRepository.save(
            db,
            review
        )

        return {
            "success": True,
            "message": "Review approved successfully"
        }

    @staticmethod
    async def reject_review(
        db,
        review_id,
        admin_note
    ):

        review = await ReviewRepository.get_by_id(
            db,
            review_id
        )

        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found"
            )

        review.status = ReviewStatus.REJECTED
        review.admin_note = admin_note

        await ReviewRepository.save(
            db,
            review
        )

        return {
            "success": True,
            "message": "Review rejected successfully"
        }

    @staticmethod
    async def flag_review(
        db,
        review_id,
        admin_note
    ):

        review = await ReviewRepository.get_by_id(
            db,
            review_id
        )

        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found"
            )

        review.status = ReviewStatus.FLAGGED
        review.admin_note = admin_note

        await ReviewRepository.save(
            db,
            review
        )

        return {
            "success": True,
            "message": "Review flagged successfully"
        }

    @staticmethod
    async def dashboard(
        db
    ):

        stats = await ReviewRepository.get_dashboard_stats(
            db
        )

        return {
            "success": True,
            "status_code": 200,
            "data": stats
        }