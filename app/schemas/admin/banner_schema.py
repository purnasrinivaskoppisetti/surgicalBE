from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class BannerRequest(BaseModel):
    title: str
    subtitle: str | None = None
    redirect_url: str | None = None
    sort_order: int = 0
    is_active: bool = True


from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID

class BannerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    subtitle: Optional[str] = None
    image_url: str
    mobile_image_url: Optional[str] = None
    redirect_url: Optional[str] = None
    sort_order: int
    is_active: bool