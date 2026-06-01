from pydantic import BaseModel, Field


class AddToCartRequest(BaseModel):

    quantity: int = Field(
        default=1,
        ge=1
    )