from app.models.models import Address
from app.repositories.address_repository import AddressRepository


class AddressService:

    @staticmethod
    async def create_address(
        db,
        user_id,
        payload
    ):

        address = Address(
            user_id=user_id,
            full_name=payload.full_name,
            phone=payload.phone,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            pincode=payload.pincode,
            country=payload.country,
            is_default=payload.is_default
        )

        address = await AddressRepository.create(
            db,
            address
        )

        return {
            "success": True,
            "status_code": 201,
            "message": "Address created successfully",
            "data": {
                "id": str(address.id)
            }
        }