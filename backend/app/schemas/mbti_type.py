from pydantic import BaseModel
from app.schemas.datetime_utils import UtcDatetime

class MbtiTypeResponse(BaseModel):
    id: int
    code: str
    name: str
    name_en: str
    description: str
    traits: list[str]
    created_at: UtcDatetime
    
    model_config = {"from_attributes": True}
