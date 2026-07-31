from datetime import datetime
from pydantic import BaseModel

class MbtiTypeResponse(BaseModel):
    id: int
    code: str
    name: str
    name_en: str
    description: str
    traits: list[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}
