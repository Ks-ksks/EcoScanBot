from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    receipt_name: str
    category: str
    co2: float

class AnalyzeResponse(BaseModel):
    status: str
    data: Optional[dict] = None
    message: Optional[str] = None

class FeedbackRequest(BaseModel):
    user_id: int
    user_name: str
    username: str
    message: str