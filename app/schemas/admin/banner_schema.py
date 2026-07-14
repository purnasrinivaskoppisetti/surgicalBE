from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class BannerRequest(BaseModel):
    title: str
    subtitle: str | None = None
    redirect_url: str | None = None
    sort_order: int = 0
    is_active: bool = True


class BannerResponse(BaseModel):
    id: UUID
    title: str
    subtitle: Optional[str]
    image_url: str
    mobile_image_url: Optional[str]
    redirect_url: Optional[str]
    sort_order: int

    class Config:
        from_attributes = True