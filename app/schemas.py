from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserIn(BaseModel):
    username: str
    password: str


class RecordIn(BaseModel):
    item: str
    amount: float


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item: str
    amount: float
    created_at: datetime


class PageOut(BaseModel):
    items: list[RecordOut]
    total: int
    page: int
    size: int
    pages: int
